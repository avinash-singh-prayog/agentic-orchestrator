"""
Personal Assistant LangGraph Agent.

A ReAct agent that uses MCP servers for weather and web search capabilities.
"""
import os
import logging
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_models import ChatLiteLLM
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config.settings import settings
from tools import PERSONAL_ASSISTANT_TOOLS

logger = logging.getLogger("personal_assistant.agent")


# Agent State
class AgentState(TypedDict):
    """State for the Personal Assistant agent."""
    messages: Annotated[list[BaseMessage], add_messages]


# System prompt
SYSTEM_PROMPT = """You are a helpful Personal Assistant with access to real-time information tools.

**Available Tools:**
1. **get_current_weather** - Get current weather for any location
2. **get_weather_forecast** - Get multi-day weather forecast
3. **web_search** - Search the web for current information
4. **read_webpage** - Read and extract content from a URL

**Guidelines:**
- Always use tools when asked about weather, forecasts, or current events
- For web searches, provide clear summaries of the results
- Be conversational and helpful
- If a tool returns an error, explain the issue clearly
- Provide concise but complete answers

**Response Format:**
- Use markdown for formatting when helpful
- Include relevant details from tool results
- Cite sources when using web search results
"""


def create_llm():
    """Create the LLM instance."""
    return ChatLiteLLM(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key or settings.groq_api_key,
        temperature=0.7,
    )


def create_agent():
    """Create the Personal Assistant LangGraph agent."""
    llm = create_llm()
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(PERSONAL_ASSISTANT_TOOLS)
    
    # Define the agent node
    def agent_node(state: AgentState) -> dict:
        """Process messages and decide on actions."""
        messages = state["messages"]
        
        # Add system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define routing logic
    def should_continue(state: AgentState) -> str:
        """Determine if we should continue to tools or end."""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(PERSONAL_ASSISTANT_TOOLS))
    
    # Add edges
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# Create the agent instance
agent = create_agent()


async def process_message(message: str) -> str:
    """
    Process a user message through the Personal Assistant agent.
    
    Args:
        message: User's message
        
    Returns:
        Agent's response
    """
    logger.info(f"Processing message: {message[:50]}...")
    
    # Run the agent
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=message)]
    })
    
    # Extract the final response
    final_message = result["messages"][-1]
    
    if isinstance(final_message, AIMessage):
        return final_message.content
    
    return str(final_message)
