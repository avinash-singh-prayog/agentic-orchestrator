"""
Booking Agent State.

LangGraph state management for the booking agent workflow.
"""

from typing import Optional, List

from langgraph.graph import MessagesState

from ..domain.models import (
    OrderRequest,
    OrderResponse,
    ExtractedOrderIntent,
)


class BookingAgentState(MessagesState):
    """
    State for the booking agent workflow.

    Extends MessagesState to include order-specific state fields.
    """

    # Extracted intent from user input
    intent: Optional[ExtractedOrderIntent] = None

    # Parsed order request for creation
    order_request: Optional[OrderRequest] = None

    # API response from order operations
    order_response: Optional[dict] = None

    # Error message if any step fails
    error: Optional[str] = None
