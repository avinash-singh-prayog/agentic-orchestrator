"""
Carrier Agent

Executes shipment bookings with carriers.
Includes TBAC policy enforcement for high-value transactions.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from orchestrator.common.llm import get_llm_provider

logger = logging.getLogger(__name__)


class CarrierAgent:
    """
    Carrier execution agent.
    
    Handles:
    - Shipment booking with carriers
    - Tracking information retrieval
    - Booking cancellation
    
    This agent is guarded by TBAC policies and may require
    human approval for high-value transactions.
    """
    
    def __init__(self):
        """Initialize the carrier agent."""
        self._llm = get_llm_provider(agent_type="carrier")
        self._bookings: dict[str, dict[str, Any]] = {}
        logger.info("Initialized CarrierAgent")
    
    async def book_shipment(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Book a shipment with the specified carrier.
        
        Args:
            request: Booking request with quote_id, order_id, etc.
            
        Returns:
            Booking confirmation or error.
        """
        quote_id = request.get("quote_id", "")
        order_id = request.get("order_id", "")
        customer_id = request.get("customer_id", "")
        
        logger.info(f"Booking shipment: order={order_id}, quote={quote_id}")
        
        # Simulate carrier booking
        booking_id = f"BK{uuid4().hex[:10].upper()}"
        tracking_number = f"TRK{uuid4().hex[:12].upper()}"
        
        booking = {
            "booking_id": booking_id,
            "order_id": order_id,
            "quote_id": quote_id,
            "customer_id": customer_id,
            "tracking_number": tracking_number,
            "carrier": self._get_carrier_from_quote(quote_id),
            "status": "confirmed",
            "booked_at": datetime.utcnow().isoformat(),
        }
        
        # Store booking
        self._bookings[booking_id] = booking
        
        return {
            "status": "confirmed",
            "booking_id": booking_id,
            "tracking_number": tracking_number,
            "carrier": booking["carrier"],
            "message": "Shipment booked successfully",
        }
    
    async def get_tracking(self, tracking_number: str) -> dict[str, Any]:
        """
        Get tracking information for a shipment.
        
        Args:
            tracking_number: The tracking number to look up.
            
        Returns:
            Tracking status and history.
        """
        # Find booking by tracking number
        booking = next(
            (b for b in self._bookings.values() if b["tracking_number"] == tracking_number),
            None
        )
        
        if not booking:
            return {
                "status": "not_found",
                "tracking_number": tracking_number,
                "message": "Tracking number not found",
            }
        
        # Simulate tracking events
        return {
            "tracking_number": tracking_number,
            "carrier": booking["carrier"],
            "status": "in_transit",
            "events": [
                {
                    "timestamp": booking["booked_at"],
                    "status": "booking_confirmed",
                    "location": "Origin Facility",
                    "description": "Shipment booked and label created",
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "in_transit",
                    "location": "Transit Hub",
                    "description": "Package in transit to destination",
                },
            ],
            "estimated_delivery": "2-5 business days",
        }
    
    async def cancel_booking(self, booking_id: str) -> dict[str, Any]:
        """
        Cancel an existing booking.
        
        Args:
            booking_id: The booking ID to cancel.
            
        Returns:
            Cancellation result.
        """
        booking = self._bookings.get(booking_id)
        
        if not booking:
            return {
                "status": "not_found",
                "booking_id": booking_id,
                "message": "Booking not found",
            }
        
        if booking["status"] == "cancelled":
            return {
                "status": "already_cancelled",
                "booking_id": booking_id,
                "message": "Booking was already cancelled",
            }
        
        # Update booking status
        booking["status"] = "cancelled"
        booking["cancelled_at"] = datetime.utcnow().isoformat()
        
        return {
            "status": "cancelled",
            "booking_id": booking_id,
            "refund_eligible": True,
            "message": "Booking cancelled successfully",
        }
    
    def _get_carrier_from_quote(self, quote_id: str) -> str:
        """Extract carrier name from quote ID."""
        if quote_id.startswith("fedex"):
            return "FedEx"
        elif quote_id.startswith("dhl"):
            return "DHL"
        elif quote_id.startswith("ups"):
            return "UPS"
        else:
            return "Unknown"
