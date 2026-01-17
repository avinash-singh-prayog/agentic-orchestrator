"""
Supervisor Agent Nodes.

Orchestrates the workflow by deciding which tool/worker to call.
"""

import logging
import os
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import Tool
from langchain_core.runnables import RunnableConfig

from .state import SupervisorAgentState
from .tools import SUPERVISOR_TOOLS
from .llm_factory import LLMFactory

logger = logging.getLogger("supervisor_agent.nodes")


def extract_llm_error_message(error: Exception) -> str:
    """Extract a user-friendly message from LLM API errors."""
    error_str = str(error)
    
    # Check for common error patterns
    if "402" in error_str or "credits" in error_str.lower():
        return "⚠️ **API Credits Exhausted**\n\nThe AI service has run out of credits. Please try again later or contact support to add more credits."
    elif "429" in error_str or "rate limit" in error_str.lower():
        return "⚠️ **Rate Limit Reached**\n\nToo many requests. Please wait a moment and try again."
    elif "401" in error_str or "unauthorized" in error_str.lower():
        return "⚠️ **Authentication Error**\n\nThere's an issue with the AI service configuration. Please contact support."
    elif "timeout" in error_str.lower():
        return "⚠️ **Request Timeout**\n\nThe AI service took too long to respond. Please try again."
    else:
        # Generic error with some detail
        return f"⚠️ **AI Service Error**\n\nUnable to process your request: {error_str[:200]}"

class SupervisorNodes:
    def __init__(self):
        self.llm = LLMFactory.get_llm("SUPERVISOR_LLM", temperature=0)
        self.tools = {t.name: t for t in SUPERVISOR_TOOLS}
        self.llm_with_tools = self.llm.bind_tools(SUPERVISOR_TOOLS)

    async def supervisor_node(self, state: SupervisorAgentState, config: RunnableConfig) -> Dict[str, Any]:
        """
        Supervisor decides next step: call tool or answer.
        """
        # Extract User context
        user_id = None
        if config and "metadata" in config:
            user_id = config["metadata"].get("user_id")

        # Dynamic LLM Initialization (per request)
        # We re-initialize here to support per-user config. 
        # Ideally we'd cache this but for now we fetch fresh.
        from app.services.llm_config_service import LLMConfigService
        
        llm_config = None
        if user_id:
            try:
                service = LLMConfigService()
                llm_config = await service.get_config(user_id)
            except Exception as e:
                logger.warning(f"Failed to fetch user LLM config: {e}. Falling back to default.")

        # Initialize LLM with tool binding
        llm = LLMFactory.get_llm("SUPERVISOR_LLM", temperature=0, llm_config=llm_config)
        llm_with_tools = llm.bind_tools(SUPERVISOR_TOOLS)

        messages = state["messages"]
        logger.info(f"Supervisor processing: {messages[-1].content[:50]}...")
        
        system_prompt = SystemMessage(content="""You are an AI Supervisor Agent.

You delegate tasks to specialized agents that you discover dynamically via the Directory Service.
You do NOT have a hardcoded list of capabilities - you discover them at runtime.

**Available Tools:**
1. `discover_capabilities()` - Query the Directory Service to see what agents and capabilities are available.
2. `delegate_to_capability(capability, message)` - Route a task to an agent with that capability.

**Workflow:**
1. If a user asks something and you're unsure what capabilities exist, use `discover_capabilities()` first.
2. Once you know the capability name, use `delegate_to_capability(capability, message)` to route the task.
3. If delegation fails (no agent found), inform the user honestly.

**CRITICAL RULES:**
1. **Agents are STATELESS**: They do not remember previous messages. You MUST include ALL relevant context in the `message` argument EVERY TIME.
2. **Context Resolution**: If the user replies with partial info (e.g., "5kg"), combine with previous context to form a COMPLETE request.
3. **No Guessing**: NEVER make up data. Only report what agents actually return.
4. **Error Reporting**: If a capability is not found or fails, report the error exactly.

**General Responses:**
- For greetings or general questions that don't need agent delegation, respond directly.
- If you discover no relevant capability exists, let the user know what IS available.
""")
        
        # Include system prompt if not present
        if not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages
        
        try:
            response = await llm_with_tools.ainvoke(messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"LLM API error in supervisor_node: {e}")
            error_message = extract_llm_error_message(e)
            return {"messages": [AIMessage(content=error_message)]}

    async def tool_node(self, state: SupervisorAgentState) -> Dict[str, Any]:
        """
        Executes tools (Worker Agent calls).
        """
        last_message = state["messages"][-1]
        
        outputs = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            if tool_name in self.tools:
                logger.info(f"Executing tool: {tool_name} with {tool_args}")
                tool_instance = self.tools[tool_name]
                # We simply pass the original user prompt to the carrier agent for now
                # In a more advanced version, we'd extract specific args.
                # The tool 'call_serviceability_agent' expects 'prompt'.
                # Ideally the LLM extracts this.
                try:
                     result = await tool_instance.ainvoke(tool_args)
                except Exception as e:
                    result = f"Error: {e}"
                
                outputs.append(
                    {
                        "tool_call_id": tool_call["id"],
                        "output": str(result),
                        "name": tool_name,
                    }
                )
        
        # Create ToolMessage implies we need to convert outputs
        # For LangGraph simple flow, we can just return the AIMessage with results or 
        # let standard ToolNode handle it. Here we do it manually to ensure formatting.
        from langchain_core.messages import ToolMessage
        tool_messages = [ToolMessage(content=o["output"], tool_call_id=o["tool_call_id"]) for o in outputs]
        
        return {"messages": tool_messages}
