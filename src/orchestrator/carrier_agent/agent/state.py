"""
Carrier Agent State.

LangGraph state management for the carrier agent workflow.
"""

from typing import Annotated, List, Optional

from langgraph.graph import MessagesState

from ..domain.models import (
    LabelResponse,
    RateQuote,
    ShipmentRequest,
)


class CarrierAgentState(MessagesState):
    """
    State for the carrier agent workflow.

    Extends MessagesState to include carrier-specific state fields.
    """

    # Parsed shipment request from user input
    request: Optional[ShipmentRequest] = None

    # Available rates from all carriers
    rates: List[RateQuote] = []

    # Raw serviceability response for dynamic generation
    serviceability_response: Optional[dict] = None

    # Selected rate for booking
    selected_rate: Optional[RateQuote] = None

    # Final booking result
    final_label: Optional[LabelResponse] = None

    # Error message if any step fails
    error: Optional[str] = None
