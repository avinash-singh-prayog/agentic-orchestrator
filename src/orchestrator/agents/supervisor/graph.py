"""
Orchestrator Supervisor LangGraph

LangGraph-based supervisor that orchestrates the logistics workflow.
Implements a ReAct-style agent with the following nodes:
- supervisor_node: Intent classification and routing
- serviceability_node: Delegates to Serviceability Agent
- rate_negotiation_node: Delegates to Rate Agent
- carrier_execution_node: Delegates to Carrier Agent
- reflection_node: Evaluates responses and decides next action
- approval_gate_node: HITL interrupt logic
"""

import json
import logging
import operator
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Annotated, Any, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from orchestrator.common.llm import get_llm_provider
from orchestrator.agents.supervisor.tools import (
    check_serviceability,
    get_shipping_rates,
    book_shipment,
    SUPERVISOR_TOOLS,
)
from orchestrator.agents.supervisor.hitl import get_hitl_manager

logger = logging.getLogger(__name__)


class NodeState(str, Enum):
    """Node states for the orchestrator workflow."""
    
    SUPERVISOR = "supervisor"
    SERVICEABILITY = "serviceability"
    RATE_NEGOTIATION = "rate_negotiation"
    CARRIER_EXECUTION = "carrier_execution"
    REFLECTION = "reflection"
    APPROVAL_GATE = "approval_gate"
    GENERAL_RESPONSE = "general_response"


class GraphState(TypedDict):
    """
    State maintained throughout the orchestration workflow.
    
    The messages field uses the reducer pattern for accumulating
    conversation history.
    """
    
    # Request tracking
    request_id: str
    
    # Order data
    order_id: str
    customer_id: str
    origin: str
    destination: str
    shipments: list[dict[str, Any]]
    
    # Workflow state
    messages: Annotated[list[dict[str, Any]], operator.add]
    is_serviceable: bool | None
    quotes: list[dict[str, Any]]
    selected_quote: dict[str, Any] | None
    approval_status: str | None
    booking_confirmation: dict[str, Any] | None
    
    # Error handling
    errors: list[str]
    
    # Routing
    next_node: str
    full_response: str


# System prompt for the supervisor
SUPERVISOR_SYSTEM_PROMPT = """You are an intelligent logistics orchestrator supervisor. Your role is to help customers with shipping orders by coordinating multiple specialized agents.

You have access to the following capabilities:
1. **Serviceability Check**: Verify if a shipping route is valid and available
2. **Rate Negotiation**: Get competitive quotes from multiple carriers
3. **Booking**: Book shipments with selected carriers (may require approval for high-value orders)

For each customer request, analyze their intent and determine the appropriate action:
- If they want to check if shipping is possible, use serviceability check
- If they want pricing/quotes, use rate negotiation
- If they want to book a shipment, coordinate the full flow (serviceability -> rates -> booking)
- If it's a general question, provide helpful information

Always be professional, clear, and proactive in helping customers.

Current order context:
- Order ID: {order_id}
- Origin: {origin}
- Destination: {destination}
- Customer ID: {customer_id}
"""


class OrchestratorGraph:
    """
    LangGraph-based orchestrator supervisor.
    
    Implements a stateful workflow for processing logistics orders
    with support for streaming responses and HITL interrupts.
    """
    
    def __init__(self):
        """Initialize the orchestrator graph."""
        self._llm = get_llm_provider(agent_type="supervisor")
        self._graph: CompiledStateGraph | None = None
        self._hitl_manager = get_hitl_manager()
        logger.info("Initialized OrchestratorGraph")
    
    @property
    def graph(self) -> CompiledStateGraph:
        """Get or build the compiled graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph StateGraph."""
        builder = StateGraph(GraphState)
        
        # Add nodes
        builder.add_node(NodeState.SUPERVISOR, self._supervisor_node)
        builder.add_node(NodeState.SERVICEABILITY, self._serviceability_node)
        builder.add_node(NodeState.RATE_NEGOTIATION, self._rate_negotiation_node)
        builder.add_node(NodeState.APPROVAL_GATE, self._approval_gate_node)
        builder.add_node(NodeState.CARRIER_EXECUTION, self._carrier_execution_node)
        builder.add_node(NodeState.REFLECTION, self._reflection_node)
        builder.add_node(NodeState.GENERAL_RESPONSE, self._general_response_node)
        
        # Add edges from START
        builder.add_edge(START, NodeState.SUPERVISOR)
        
        # Add conditional edges from supervisor
        builder.add_conditional_edges(
            NodeState.SUPERVISOR,
            self._route_from_supervisor,
            {
                NodeState.SERVICEABILITY: NodeState.SERVICEABILITY,
                NodeState.RATE_NEGOTIATION: NodeState.RATE_NEGOTIATION,
                NodeState.CARRIER_EXECUTION: NodeState.APPROVAL_GATE,
                NodeState.GENERAL_RESPONSE: NodeState.GENERAL_RESPONSE,
                END: END,
            }
        )
        
        # Serviceability -> Reflection
        builder.add_edge(NodeState.SERVICEABILITY, NodeState.REFLECTION)
        
        # Rate Negotiation -> Reflection
        builder.add_edge(NodeState.RATE_NEGOTIATION, NodeState.REFLECTION)
        
        # Approval Gate -> conditional
        builder.add_conditional_edges(
            NodeState.APPROVAL_GATE,
            self._route_from_approval,
            {
                NodeState.CARRIER_EXECUTION: NodeState.CARRIER_EXECUTION,
                "wait_approval": END,  # Suspend for HITL
            }
        )
        
        # Carrier Execution -> Reflection
        builder.add_edge(NodeState.CARRIER_EXECUTION, NodeState.REFLECTION)
        
        # Reflection -> conditional
        builder.add_conditional_edges(
            NodeState.REFLECTION,
            self._route_from_reflection,
            {
                NodeState.SUPERVISOR: NodeState.SUPERVISOR,
                END: END,
            }
        )
        
        # General Response -> END
        builder.add_edge(NodeState.GENERAL_RESPONSE, END)
        
        return builder.compile()
    
    # ===========================
    # Node Implementations
    # ===========================
    
    async def _supervisor_node(self, state: GraphState) -> dict[str, Any]:
        """
        Supervisor node: Classifies intent and routes to appropriate node.
        """
        logger.info(f"Supervisor node processing request: {state.get('request_id')}")
        
        # Prepare conversation history
        messages = [
            {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT.format(
                order_id=state.get("order_id", "N/A"),
                origin=state.get("origin", "N/A"),
                destination=state.get("destination", "N/A"),
                customer_id=state.get("customer_id", "N/A"),
            )}
        ]
        messages.extend(state.get("messages", []))
        
        # Get LLM decision
        classification_prompt = """Based on the conversation, determine the next action.
Respond with a JSON object:
{
    "intent": "serviceability_check" | "rate_request" | "book_shipment" | "general_info",
    "reasoning": "brief explanation",
    "extract_params": {
        "origin": "if mentioned",
        "destination": "if mentioned",
        "weight_kg": "if mentioned"
    }
}"""
        
        messages.append({"role": "user", "content": classification_prompt})
        
        response = await self._llm.generate_response(
            messages=messages,
            json_schema={"type": "object"},
            temperature=0.3,
        )
        
        # Parse response
        try:
            decision = json.loads(response)
            intent = decision.get("intent", "general_info")
            extracted = decision.get("extract_params", {})
        except json.JSONDecodeError:
            intent = "general_info"
            extracted = {}
        
        # Map intent to next node
        intent_to_node = {
            "serviceability_check": NodeState.SERVICEABILITY,
            "rate_request": NodeState.RATE_NEGOTIATION,
            "book_shipment": NodeState.CARRIER_EXECUTION,
            "general_info": NodeState.GENERAL_RESPONSE,
        }
        
        next_node = intent_to_node.get(intent, NodeState.GENERAL_RESPONSE)
        
        # Update state with extracted params
        updates: dict[str, Any] = {
            "next_node": next_node,
        }
        
        if extracted.get("origin"):
            updates["origin"] = extracted["origin"]
        if extracted.get("destination"):
            updates["destination"] = extracted["destination"]
        
        return updates
    
    async def _serviceability_node(self, state: GraphState) -> dict[str, Any]:
        """
        Serviceability node: Check if route is serviceable.
        """
        logger.info(f"Serviceability check: {state.get('origin')} -> {state.get('destination')}")
        
        result = await check_serviceability.ainvoke({
            "origin": state.get("origin", ""),
            "destination": state.get("destination", ""),
            "shipment_type": "standard",
        })
        
        is_serviceable = result.get("is_serviceable", False)
        
        response_msg = {
            "role": "assistant",
            "content": f"Serviceability check complete. Route from {state.get('origin')} to {state.get('destination')} is {'serviceable' if is_serviceable else 'not serviceable'}. " + (
                f"Available carriers: {', '.join(result.get('available_carriers', []))}"
                if is_serviceable else
                f"Reason: {', '.join(result.get('reasons', ['Unknown']))}"
            ),
        }
        
        return {
            "is_serviceable": is_serviceable,
            "messages": [response_msg],
        }
    
    async def _rate_negotiation_node(self, state: GraphState) -> dict[str, Any]:
        """
        Rate negotiation node: Get quotes from carriers.
        """
        logger.info(f"Getting rates: {state.get('origin')} -> {state.get('destination')}")
        
        # Calculate total weight from shipments
        total_weight = 0.0
        for shipment in state.get("shipments", []):
            for item in shipment.get("items", []):
                total_weight += item.get("weight", 0) * item.get("quantity", 1)
        
        if total_weight == 0:
            total_weight = 10.0  # Default weight
        
        result = await get_shipping_rates.ainvoke({
            "origin": state.get("origin", ""),
            "destination": state.get("destination", ""),
            "weight_kg": total_weight,
            "shipment_type": "standard",
        })
        
        quotes = result.get("quotes", [])
        best = result.get("best_price", {})
        fastest = result.get("fastest", {})
        
        response_msg = {
            "role": "assistant",
            "content": f"I found {len(quotes)} quotes for your shipment:\n" + "\n".join([
                f"- {q['carrier']} {q['service']}: ${q['price']} ({q['estimated_days']} days)"
                for q in quotes
            ]) + f"\n\nBest price: {best.get('carrier')} at ${best.get('price')}\nFastest: {fastest.get('carrier')} ({fastest.get('estimated_days')} days)",
        }
        
        return {
            "quotes": quotes,
            "messages": [response_msg],
        }
    
    async def _approval_gate_node(self, state: GraphState) -> dict[str, Any]:
        """
        Approval gate node: Check if HITL approval is needed.
        """
        from orchestrator.common.config import settings
        
        # Calculate order value
        order_value = sum(
            item.get("value", 0) * item.get("quantity", 1)
            for shipment in state.get("shipments", [])
            for item in shipment.get("items", [])
        )
        
        # If no value set, use a default for demo
        if order_value == 0:
            order_value = 1000.0
        
        needs_approval = order_value > settings.max_auto_approval_limit
        
        if needs_approval:
            # Create HITL interrupt
            hitl_interrupt = await self._hitl_manager.create_interrupt(
                order_id=state.get("order_id", "unknown"),
                reason=f"Order value (${order_value}) exceeds auto-approval limit (${settings.max_auto_approval_limit})",
                action="book_shipment",
                context={
                    "order_value": order_value,
                    "selected_quote": state.get("selected_quote"),
                    "origin": state.get("origin"),
                    "destination": state.get("destination"),
                },
            )
            
            logger.info(f"HITL interrupt created: {hitl_interrupt.interrupt_id}")
            
            response_msg = {
                "role": "assistant",
                "content": f"This order requires manager approval due to its value (${order_value}). "
                           f"Approval request ID: {hitl_interrupt.interrupt_id}. "
                           "I'll notify you once approved.",
            }
            
            return {
                "approval_status": "pending",
                "messages": [response_msg],
            }
        
        return {
            "approval_status": "auto_approved",
        }
    
    async def _carrier_execution_node(self, state: GraphState) -> dict[str, Any]:
        """
        Carrier execution node: Book the shipment.
        """
        logger.info(f"Booking shipment for order: {state.get('order_id')}")
        
        selected_quote = state.get("selected_quote")
        if not selected_quote and state.get("quotes"):
            # Auto-select best price if not specified
            selected_quote = min(state["quotes"], key=lambda q: q.get("price", float("inf")))
        
        # Calculate order value
        order_value = sum(
            item.get("value", 0) * item.get("quantity", 1)
            for shipment in state.get("shipments", [])
            for item in shipment.get("items", [])
        )
        
        if order_value == 0:
            order_value = 1000.0
        
        result = await book_shipment.ainvoke({
            "quote_id": selected_quote.get("quote_id", "auto_001") if selected_quote else "auto_001",
            "order_id": state.get("order_id", str(uuid4())),
            "customer_id": state.get("customer_id", "unknown"),
            "order_value": order_value,
        })
        
        if result.get("status") == "confirmed":
            response_msg = {
                "role": "assistant",
                "content": f"✅ Shipment booked successfully!\n"
                           f"Booking ID: {result.get('booking_id')}\n"
                           f"Tracking Number: {result.get('tracking_number')}\n"
                           f"Carrier: {result.get('carrier')}",
            }
        else:
            response_msg = {
                "role": "assistant",
                "content": result.get("message", "Booking in progress..."),
            }
        
        return {
            "booking_confirmation": result,
            "messages": [response_msg],
        }
    
    async def _reflection_node(self, state: GraphState) -> dict[str, Any]:
        """
        Reflection node: Evaluate the current state and decide next action.
        """
        # Check if workflow is complete
        is_complete = False
        
        booking_confirmation = state.get("booking_confirmation")
        if booking_confirmation and booking_confirmation.get("status") == "confirmed":
            is_complete = True
        elif state.get("is_serviceable") is False:
            is_complete = True
        elif state.get("approval_status") == "pending":
            is_complete = True
        # Also complete if we have a serviceability check result (positive)
        elif state.get("is_serviceable") is True:
            is_complete = True
        # Complete if we have quotes (rate inquiry complete)
        elif state.get("quotes"):
            is_complete = True
        
        return {
            "next_node": END if is_complete else NodeState.SUPERVISOR,
        }
    
    async def _general_response_node(self, state: GraphState) -> dict[str, Any]:
        """
        General response node: Handle general queries.
        """
        messages = [
            {"role": "system", "content": "You are a helpful logistics assistant. Answer the user's question about shipping, logistics, or your capabilities."}
        ]
        messages.extend(state.get("messages", []))
        
        response = await self._llm.generate_response(
            messages=messages,
            temperature=0.7,
        )
        
        return {
            "messages": [{"role": "assistant", "content": response}],
            "full_response": response,
        }
    
    # ===========================
    # Routing Functions
    # ===========================
    
    def _route_from_supervisor(self, state: GraphState) -> str:
        """Route from supervisor based on classified intent."""
        return state.get("next_node", NodeState.GENERAL_RESPONSE)
    
    def _route_from_approval(self, state: GraphState) -> str:
        """Route from approval gate."""
        if state.get("approval_status") == "pending":
            return "wait_approval"
        return NodeState.CARRIER_EXECUTION
    
    def _route_from_reflection(self, state: GraphState) -> str:
        """Route from reflection node."""
        return state.get("next_node", END)
    
    # ===========================
    # Public Interface
    # ===========================
    
    async def serve(self, prompt: str, context: dict[str, Any] | None = None) -> str:
        """
        Process a prompt and return the response.
        
        Args:
            prompt: User prompt.
            context: Optional context (order_id, customer_id, etc.).
            
        Returns:
            The final response string.
        """
        context = context or {}
        
        initial_state: GraphState = {
            "request_id": str(uuid4()),
            "order_id": context.get("order_id", str(uuid4())[:8]),
            "customer_id": context.get("customer_id", "guest"),
            "origin": context.get("origin", ""),
            "destination": context.get("destination", ""),
            "shipments": context.get("shipments", []),
            "messages": [{"role": "user", "content": prompt}],
            "is_serviceable": None,
            "quotes": [],
            "selected_quote": None,
            "approval_status": None,
            "booking_confirmation": None,
            "errors": [],
            "next_node": "",
            "full_response": "",
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        # Extract final response from messages
        assistant_messages = [
            m["content"] for m in result.get("messages", [])
            if m.get("role") == "assistant"
        ]
        
        return assistant_messages[-1] if assistant_messages else "I couldn't process your request."
    
    async def streaming_serve(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Process a prompt and stream the response.
        
        Args:
            prompt: User prompt.
            context: Optional context.
            
        Yields:
            Response chunks.
        """
        context = context or {}
        
        initial_state: GraphState = {
            "request_id": str(uuid4()),
            "order_id": context.get("order_id", str(uuid4())[:8]),
            "customer_id": context.get("customer_id", "guest"),
            "origin": context.get("origin", ""),
            "destination": context.get("destination", ""),
            "shipments": context.get("shipments", []),
            "messages": [{"role": "user", "content": prompt}],
            "is_serviceable": None,
            "quotes": [],
            "selected_quote": None,
            "approval_status": None,
            "booking_confirmation": None,
            "errors": [],
            "next_node": "",
            "full_response": "",
        }
        
        async for event in self.graph.astream(initial_state):
            for node_name, node_output in event.items():
                if "messages" in node_output:
                    for msg in node_output["messages"]:
                        if msg.get("role") == "assistant":
                            yield msg["content"]
