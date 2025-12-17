"""
Booking Agent Graph.

LangGraph workflow for order operations.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from .state import BookingAgentState
from .nodes import BookingNodes
from ..config.settings import settings

logger = logging.getLogger("booking_agent.graph")

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


@agent(name="booking_agent")
class BookingGraph:
    """LangGraph workflow for order operations."""

    def __init__(self):
        self.nodes = BookingNodes()
        self.app = self._build()

    @graph(name="order_workflow")
    def _build(self) -> StateGraph:
        """Build and compile the workflow graph."""
        workflow = StateGraph(BookingAgentState)

        # Add nodes
        workflow.add_node("parse", self.nodes.parse_request)
        workflow.add_node("create", self.nodes.create_order)
        workflow.add_node("get", self.nodes.get_order)
        workflow.add_node("cancel", self.nodes.cancel_order)
        workflow.add_node("generate", self.nodes.generate_response)

        # Set entry point
        workflow.set_entry_point("parse")

        # Conditional routing based on parse result
        workflow.add_conditional_edges(
            "parse",
            self._route_action,
            {
                "create": "create",
                "get": "get",
                "cancel": "cancel",
                "error": END,
            },
        )

        # All action nodes lead to generate response
        workflow.add_edge("create", "generate")
        workflow.add_edge("get", "generate")
        workflow.add_edge("cancel", "generate")
        
        # Generate leads to END
        workflow.add_edge("generate", END)

        logger.info("Built booking agent graph")
        return workflow.compile()

    def _route_action(self, state: BookingAgentState) -> Literal["create", "get", "cancel", "error"]:
        """Route to appropriate action based on parsed intent."""
        if state.get("error") or not state.get("intent"):
            return "error"
        
        intent = state["intent"]
        action = intent.action.lower()
        
        if action == "create":
            return "create"
        elif action == "cancel":
            return "cancel"
        elif action in ("get", "list", "status"):
            return "get"
        else:
            return "get"  # Default to get for unknown actions

    async def invoke(self, user_message: str) -> dict:
        """Invoke the booking agent with a user message."""
        initial_state = {"messages": [("user", user_message)]}
        return await self.app.ainvoke(initial_state)
