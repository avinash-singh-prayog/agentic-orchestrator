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
        - "call_transaction_rca_agent": Transaction RCA Agent. Performs root cause analysis on unprocessed transactions. REQUIRED: Complete transaction context JSON with transaction_id, checkpoints, merchant_config, merchant_data, external_signals, risk_indicators.
        
        CRITICAL RULES:
        1. **Worker Agents are STATELESS**: They do not remember previous messages. You MUST include ALL relevant context (locations, weight, order IDs, partner_code, transaction context, etc.) in the `prompt` or `transaction_context_json` argument EVERY TIME you call a worker.
        2. **Context Resolution**: If the user replies with just "5kg" or "New York", you must combine this with previous messages (e.g., "Check rates from 10001 to 20002") to form a COMPLETE request like "Check rates from 10001 to 20002 for 5kg" before calling the agent.
        3. **Don't ask redundant questions**: If you have the info in history, USE IT.
        4. **PARTNER CODE FOR BOOKING**: When the user wants to book/create an order after seeing serviceability results:
           - The serviceability response contains `partner_code` for each carrier (e.g., "smile_hubops", "delhivery").
           - You MUST extract and include the `partner_code` in your booking request.
           - Format: "Create order with partner_code=<code>, origin=<details>, destination=<details>, weight=<weight>"
        5. **TRANSACTION RCA ANALYSIS**: When the user asks for root cause analysis, RCA, or transaction analysis:
           - You MUST call `call_transaction_rca_agent` with a complete JSON string containing the transaction context.
           - The transaction_context_json must include: transaction_id, checkpoints (list with checkpoint_name, status, timestamp, details), and optional merchant_config, merchant_data, external_signals, risk_indicators, observational_notes.
           - Format the JSON properly as a string before passing to the tool.
           - **TICKET CREATION AFTER RCA**: If the user wants to create a ticket after RCA analysis:
             - Extract the RCA analysis JSON from the previous Transaction RCA Agent response
             - Call `call_transaction_rca_agent` again with a JSON string containing both the ticket creation request and the RCA analysis:
               {
                 "action": "create_ticket",
                 "rca_analysis": {<full RCA analysis from previous response>},
                 "transaction_context": {<original transaction context if available>}
               }
             - The Transaction RCA Agent will use the RCA output to create the ticket.
           - **RCA RESPONSE FORMATTING**: When you receive a JSON response from the Transaction RCA Agent, format it as follows (include ALL fields from the JSON):
             
             "The root cause analysis indicates [brief summary from transaction_narrative].
             
             **Key Findings:**
             - **RCA Category:** [rca_category]
             - **Confidence Level:** [confidence]
             - **Transaction Narrative:** [transaction_narrative]
             - **Last Successful Checkpoint:** [last_successful_checkpoint]
             - **Key Anomalies:**
               [List each item from key_anomalies array, each on a new line with "- " prefix]
             - **Evidence:**
               [List each item from evidence array, each on a new line with "- " prefix]
             - **Alternative Causes Considered:**
               [List each item from alternative_causes_considered array, each on a new line with "- " prefix, or "None" if the array is empty]
             - **Contradictions Observed:**
               [List each item from contradictions_observed array, each on a new line with "- " prefix, or "None" if the array is empty or missing]
             
             **Final Reasoning:** [final_reasoning]
             
             [human_intervention.prompt]"
        
        ANTI-HALLUCINATION & ROUTING ENFORCEMENT:
        - **NEVER guess specific rates or prices.** You DO NOT know any rates. You MUST call `call_serviceability_agent` to get them.
        - **NEVER claim an order is created** without calling `call_booking_agent` and receiving a success response.
        - **NEVER claim to know the root cause** of a transaction issue without calling `call_transaction_rca_agent` with proper transaction context.
        - If the user asks for "rates", "price", "shipping cost", "couriers", "serviceability" -> YOU MUST CALL `call_serviceability_agent`.
        - If the user asks to "book", "ship", "create order", "cancel", "status" -> YOU MUST CALL `call_booking_agent`.
        - If the user asks for "RCA", "root cause", "transaction analysis", "why transaction failed", "analyze transaction" -> YOU MUST CALL `call_transaction_rca_agent`.
        - **CRITICAL: TICKET CREATION AFTER RCA**: If the user wants to "create a ticket" or says "yes" to ticket creation AFTER an RCA analysis has been performed, you MUST call `call_transaction_rca_agent` (NOT `call_booking_agent`). The Transaction RCA Agent will use the RCA output to create the ticket. Pass the user's ticket creation request along with the previous RCA context.
        - **If a tool fails or returns an error**, REPORT IT exactly. Do not make up a success story.
        
        Routing Guidelines:
        - If user asks about shipping RATES, SERVICEABILITY, or CARRIER availability → call_serviceability_agent
        - If user wants to CREATE an ORDER, BOOK a shipment, check ORDER STATUS, or CANCEL an order → call_booking_agent (include partner_code!)
        - If user asks for TRANSACTION RCA, ROOT CAUSE ANALYSIS, or transaction failure analysis → call_transaction_rca_agent (include complete transaction context JSON!)
        - If user wants to CREATE A TICKET after RCA analysis has been done → call_transaction_rca_agent (NOT booking_agent! The Transaction RCA Agent handles ticket creation using RCA output)
        - If it's a general greeting or question, answer directly.
        """)
        
        # Include system prompt if not present
        if not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages
        
        try:
            response = await self.llm_with_tools.ainvoke(messages)
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
