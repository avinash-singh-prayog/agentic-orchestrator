"""
Supervisor Agent Nodes.

Orchestrates the workflow by deciding which tool/worker to call.
"""

import logging
import os
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import Tool

from .state import SupervisorAgentState
from .tools import SUPERVISOR_TOOLS
from .llm_factory import LLMFactory

logger = logging.getLogger("supervisor_agent.nodes")

class SupervisorNodes:
    def __init__(self):
        self.llm = LLMFactory.get_llm("SUPERVISOR_LLM", temperature=0)
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
        - "call_serviceability_agent": Serviceability Agent. Checks rates, serviceability, or carrier availability. REQUIRED: Origin PC, Dest PC, Weight.
        - "call_booking_agent": Booking Agent. Creates orders, checks status, or cancels orders. REQUIRED: Order details INCLUDING partner_code.
        
        CRITICAL RULES:
        1. **Worker Agents are STATELESS**: They do not remember previous messages. You MUST include ALL relevant context (locations, weight, order IDs, partner_code, etc.) in the `prompt` argument EVERY TIME you call a worker.
        2. **Context Resolution**: If the user replies with just "5kg" or "New York", you must combine this with previous messages (e.g., "Check rates from 10001 to 20002") to form a COMPLETE request like "Check rates from 10001 to 20002 for 5kg" before calling the agent.
        3. **Don't ask redundant questions**: If you have the info in history, USE IT.
        4. **PARTNER CODE FOR BOOKING**: When the user wants to book/create an order after seeing serviceability results:
           - The serviceability response contains `partner_code` for each carrier (e.g., "smile_hubops", "delhivery").
           - You MUST extract and include the `partner_code` in your booking request.
           - Format: "Create order with partner_code=<code>, origin=<details>, destination=<details>, weight=<weight>"
        
        ANTI-HALLUCINATION & ROUTING ENFORCEMENT:
        - **NEVER guess specific rates or prices.** You DO NOT know any rates. You MUST call `call_serviceability_agent` to get them.
        - **NEVER claim an order is created** without calling `call_booking_agent` and receiving a success response.
        - If the user asks for "rates", "price", "shipping cost", "couriers", "serviceability" -> YOU MUST CALL `call_serviceability_agent`.
        - If the user asks to "book", "ship", "create order", "cancel", "status" -> YOU MUST CALL `call_booking_agent`.
        - **If a tool fails or returns an error**, REPORT IT exactly. Do not make up a success story.
        
        Routing Guidelines:
        - If user asks about shipping RATES, SERVICEABILITY, or CARRIER availability → call_serviceability_agent
        - If user wants to CREATE an ORDER, BOOK a shipment, check ORDER STATUS, or CANCEL an order → call_booking_agent (include partner_code!)
        - If it's a general greeting or question, answer directly.
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
