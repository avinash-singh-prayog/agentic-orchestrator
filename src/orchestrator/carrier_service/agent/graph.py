"""
Carrier Agent Graph.

LangGraph workflow definition for the carrier agent.
Orchestrates the shipment flow: parse -> rates -> book.

Uses observability decorators for tracing when IOA-Observe SDK is available.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from orchestrator.carrier_service.agent.nodes import CarrierNodes
from orchestrator.carrier_service.agent.state import CarrierAgentState
from orchestrator.carrier_service.infra.factory import CarrierFactory

logger = logging.getLogger("carrier_agent.graph")


# Try to import observability decorators (optional dependency)
try:
    from ioa_observe.sdk.decorators import agent, graph
    HAS_OBSERVABILITY = True
    logger.info("IOA Observe SDK loaded - observability enabled")
except ImportError:
    # Fallback: Create no-op decorators if SDK not available
    def agent(name: str = ""):
        def decorator(cls):
            return cls
        return decorator
    
    def graph(name: str = ""):
        def decorator(func):
            return func
        return decorator
    
    HAS_OBSERVABILITY = False
    logger.warning("IOA Observe SDK not found - observability disabled")


@agent(name="carrier_service")
class CarrierGraph:
    """
    LangGraph workflow for carrier operations.

    Flow:
        parse -> rates -> (conditional) -> book -> END

    If rates are found, proceed to booking.
    If no rates or error, end immediately.
    
    Observability:
        - @agent decorator: Registers this class for tracing
        - @graph decorator: Traces graph execution
    """

    def __init__(self, factory: CarrierFactory | None = None):
        self.factory = factory or CarrierFactory()
        self.nodes = CarrierNodes(self.factory)
        self.app = self._build()

    @graph(name="shipment_workflow")
    def _build(self) -> StateGraph:
        """Build and compile the workflow graph."""
        workflow = StateGraph(CarrierAgentState)

        # Add nodes
        workflow.add_node("parse", self.nodes.parse_request)
        workflow.add_node("rates", self.nodes.fetch_rates)
        workflow.add_node("book", self.nodes.book_shipment)

        # Define flow
        workflow.set_entry_point("parse")

        # Conditional edge after parse
        workflow.add_conditional_edges(
            "parse",
            self._check_parse_result,
            {
                "continue": "rates",
                "error": END,
            },
        )

        # Conditional edge after rates
        workflow.add_conditional_edges(
            "rates",
            self._check_rates_result,
            {
                "book": "book",
                "end": END,
            },
        )

        # Book always ends
        workflow.add_edge("book", END)

        logger.info("Built carrier agent graph")
        return workflow.compile()

    def _check_parse_result(
        self, state: CarrierAgentState
    ) -> Literal["continue", "error"]:
        """Check if parsing succeeded."""
        if state.get("error") or not state.get("request"):
            return "error"
        return "continue"

    def _check_rates_result(
        self, state: CarrierAgentState
    ) -> Literal["book", "end"]:
        """Check if rates were found."""
        if state.get("rates"):
            return "book"
        return "end"

    async def invoke(self, user_message: str) -> dict:
        """
        Invoke the carrier agent with a user message.

        Args:
            user_message: Natural language shipping request

        Returns:
            Final state dictionary with results
        """
        initial_state = {
            "messages": [("user", user_message)],
        }
        return await self.app.ainvoke(initial_state)
