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
        
        system_prompt = SystemMessage(content="""You are a Transaction Analysis Supervisor for PineLabs.
        Your goal is to help the user by orchestrating the Transaction RCA Agent for root cause analysis of unprocessed transactions.
        
        Available Workers:
        - "call_transaction_rca_agent": Transaction RCA Agent. Performs root cause analysis on unprocessed transactions. REQUIRED: Complete transaction context JSON with transaction_id, checkpoints, merchant_config, merchant_data, external_signals, risk_indicators.
        
        CRITICAL RULES:
        1. **Worker Agents are STATELESS**: They do not remember previous messages. You MUST include ALL relevant context (transaction context, checkpoints, merchant data, etc.) in the `transaction_context_json` argument EVERY TIME you call the worker.
        2. **Context Resolution**: If the user provides partial transaction information, you must combine it with previous messages to form a COMPLETE transaction context JSON before calling the agent.
        3. **Don't ask redundant questions**: If you have the info in history, USE IT.
        4. **TRANSACTION RCA ANALYSIS**: When the user asks for root cause analysis, RCA, or transaction analysis:
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
           - **RCA RESPONSE FORMATTING**: When you receive a response from the Transaction RCA Agent:
             - If the response is already formatted in a human-readable way (with headers, sections, bullet points), present it to the user AS-IS. Do not reformat it.
             - If the response is JSON, parse it and format it in a clear, readable way. Extract the key information and present it naturally:
               
               Start with: "Based on the root cause analysis, [brief summary from transaction_narrative]"
               
               Then present:
               - **Category:** [rca_category]
               - **Confidence:** [confidence as percentage, e.g., "80%" for 0.8]
               - **Last Successful Step:** [last_successful_checkpoint, formatted nicely]
               
               **Issues Found:**
               [List each key_anomalies item as a bullet point]
               
               **Evidence:**
               [List each evidence item as a numbered list or bullet points]
               
               [If alternative_causes_considered exists and is not empty:]
               **Other Causes Considered:**
               [List each alternative_causes_considered item as a bullet point]
               
               [If contradictions_observed exists and is not empty:]
               **⚠️ Contradictions:**
               [List each contradictions_observed item as a bullet point]
               
               **Conclusion:**
               [final_reasoning]
               
               [human_intervention.prompt]
               
             - Always make the output easy to read and understand. Use clear section headers, bullet points, and natural language. Avoid technical jargon when possible.
        
        ANTI-HALLUCINATION & ROUTING ENFORCEMENT:
        - **NEVER claim to know the root cause** of a transaction issue without calling `call_transaction_rca_agent` with proper transaction context.
        - If the user asks for "RCA", "root cause", "transaction analysis", "why transaction failed", "analyze transaction", "transaction issue" -> YOU MUST CALL `call_transaction_rca_agent`.
        - **CRITICAL: TICKET CREATION AFTER RCA**: If the user wants to "create a ticket" or says "yes" to ticket creation AFTER an RCA analysis has been performed, you MUST call `call_transaction_rca_agent`. The Transaction RCA Agent will use the RCA output to create the ticket. Pass the user's ticket creation request along with the previous RCA context.
        - **If a tool fails or returns an error**, REPORT IT exactly. Do not make up a success story.
        
        Routing Guidelines:
        - If user asks for TRANSACTION RCA, ROOT CAUSE ANALYSIS, transaction failure analysis, or transaction debugging → call_transaction_rca_agent (include complete transaction context JSON!)
        - If user wants to CREATE A TICKET after RCA analysis has been done → call_transaction_rca_agent (The Transaction RCA Agent handles ticket creation using RCA output)
        - If it's a general greeting or question about transactions, answer directly. For transaction analysis, always use the Transaction RCA Agent.
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
