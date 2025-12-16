"""
Supervisor Agent Nodes.

Orchestrates the workflow by deciding which tool/worker to call.
"""

import logging
import os
from typing import Dict, Any
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import Tool

from .state import SupervisorAgentState
from .tools import SUPERVISOR_TOOLS

logger = logging.getLogger("supervisor_agent.nodes")

# LLM Config
SUPERVISOR_LLM = os.getenv("SUPERVISOR_LLM", "openrouter/openai/gpt-4o-mini")

class SupervisorNodes:
    def __init__(self):
        self.llm = ChatLiteLLM(model=SUPERVISOR_LLM, temperature=0)
        self.tools = {t.name: t for t in SUPERVISOR_TOOLS}
        self.llm_with_tools = self.llm.bind_tools(SUPERVISOR_TOOLS)

    async def supervisor_node(self, state: SupervisorAgentState) -> Dict[str, Any]:
        """
        Supervisor decides next step: call tool or answer.
        """
        messages = state["messages"]
        logger.info(f"Supervisor processing: {messages[-1].content[:50]}...")
        
        system_prompt = SystemMessage(content="""You are a Logistics Supervisor.
        Your goal is to help the user by orchestrating specialized worker agents.
        
        Available Workers:
        - "check_serviceability": Carrier Agent. Use this to check rates, serviceability, or book shipments.
        
        If the user's request requires shipping info, CALL THE TOOL.
        If it's a general greeting, answer directly.
        """)
        
        # Include system prompt if not present
        if not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages
            
        response = await self.llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

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
                # The tool 'call_carrier_agent' expects 'prompt'.
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
