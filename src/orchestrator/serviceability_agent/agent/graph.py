"""
Serviceability Agent Graph.

LangGraph workflow using tools for serviceability operations.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from .state import ServiceabilityAgentState
from .nodes import ServiceabilityNodes
from ..config.settings import settings

logger = logging.getLogger("serviceability_agent.graph")

# Try to import observability decorators
try:
    from ioa_observe.sdk.decorators import agent, graph
    HAS_OBSERVABILITY = True
    logger.info("IOA Observe SDK loaded - observability enabled")
except ImportError:
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


@agent(name="serviceability_agent")
class ServiceabilityGraph:
    """LangGraph workflow for carrier operations using tools."""

    def __init__(self):
        self.nodes = ServiceabilityNodes()
        self.app = self._build()

    @graph(name="shipment_workflow")
    def _build(self) -> StateGraph:
        """Build and compile the workflow graph."""
        workflow = StateGraph(ServiceabilityAgentState)

        workflow.add_node("parse", self.nodes.parse_request)
        workflow.add_node("rates", self.nodes.fetch_rates)
        workflow.add_node("generate", self.nodes.generate_response)
        workflow.add_node("book", self.nodes.book_shipment)

        workflow.set_entry_point("parse")

        workflow.add_conditional_edges(
            "parse",
            self._check_parse_result,
            {"continue": "rates", "error": END},
        )

        workflow.add_conditional_edges(
            "rates",
            self._check_rates_result,
            {"book": "book", "generate": "generate", "end": END},
        )
        
        workflow.add_edge("generate", END)

        workflow.add_edge("book", END)

        logger.info("Built serviceability agent graph")
        return workflow.compile()

    def _check_parse_result(self, state: ServiceabilityAgentState) -> Literal["continue", "error"]:
        if state.get("error") or not state.get("request"):
            return "error"
        return "continue"

    def _check_rates_result(self, state: ServiceabilityAgentState) -> Literal["book", "generate", "end"]:
        # For now, end after fetching rates to avoid auto-booking stub message
        if state.get("serviceability_response"):
            return "generate"
        return "end"

    async def invoke(self, user_message: str) -> dict:
        """Invoke the carrier agent with a user message."""
        initial_state = {"messages": [("user", user_message)]}
        return await self.app.ainvoke(initial_state)
