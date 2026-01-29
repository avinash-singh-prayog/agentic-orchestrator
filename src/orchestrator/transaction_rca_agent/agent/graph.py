"""
Transaction RCA Agent Graph.

LangGraph workflow for transaction root cause analysis.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from agent.state import TransactionRCAAgentState
from agent.nodes import TransactionRCANodes
from config.settings import settings

logger = logging.getLogger("transaction_rca_agent.graph")

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


@agent(name="transaction_rca_agent")
class TransactionRCAGraph:
    """LangGraph workflow for transaction RCA analysis."""

    def __init__(self):
        self.nodes = TransactionRCANodes()
        self.app = self._build()

    @graph(name="rca_workflow")
    def _build(self) -> StateGraph:
        """Build and compile the workflow graph."""
        workflow = StateGraph(TransactionRCAAgentState)

        # Add nodes
        workflow.add_node("parse", self.nodes.parse_request)
        workflow.add_node("analyze", self.nodes.analyze_rca)
        workflow.add_node("create_ticket", self.nodes.create_ticket)
        workflow.add_node("generate", self.nodes.generate_response)

        # Set entry point
        workflow.set_entry_point("parse")

        # Conditional routing based on parse result
        workflow.add_conditional_edges(
            "parse",
            self._route_after_parse,
            {
                "analyze": "analyze",
                "create_ticket": "create_ticket",
                "error": END,
            },
        )

        # Analyze always goes to generate
        workflow.add_edge("analyze", "generate")
        
        # Ticket creation goes to generate
        workflow.add_edge("create_ticket", "generate")

        # Generate leads to END
        workflow.add_edge("generate", END)

        logger.info("Built transaction RCA agent graph")
        return workflow.compile()

    def _route_after_parse(
        self, state: TransactionRCAAgentState
    ) -> Literal["analyze", "create_ticket", "error"]:
        """Route based on parse result - either analyze or create ticket."""
        # Check for error first
        if state.get("error"):
            return "error"
        
        # Check if this is a ticket creation request
        action = state.get("action")
        if action == "create_ticket":
            return "create_ticket"
        
        # Check if we have transaction context for RCA analysis
        if state.get("transaction_context"):
            return "analyze"
        
        # No transaction context and not ticket creation = error
        return "error"

    async def invoke(self, user_message: str) -> dict:
        """Invoke the transaction RCA agent with a user message."""
        from langchain_core.messages import HumanMessage
        initial_state = {"messages": [HumanMessage(content=user_message)]}
        return await self.app.ainvoke(initial_state)
