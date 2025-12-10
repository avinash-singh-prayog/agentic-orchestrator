"""
OASF Agent Card for the Carrier Agent.
"""

from typing import Any

CARRIER_AGENT_CARD: dict[str, Any] = {
    "name": "carrier-agent",
    "version": "1.0.0",
    "description": "Executes shipment bookings with carriers, with HITL support for high-value orders",
    "url": "http://localhost:9003",
    
    "capabilities": {
        "streaming": False,
        "pushNotifications": True,
        "stateTransitionHistory": True,
    },
    
    "skills": [
        {
            "id": "logistics/transport/booking",
            "name": "Shipment Booking",
            "description": "Book a shipment with a carrier",
            "tags": ["booking", "transaction", "shipping"],
        },
        {
            "id": "logistics/transport/tracking",
            "name": "Shipment Tracking",
            "description": "Get tracking information for a shipment",
            "tags": ["tracking", "status"],
        },
        {
            "id": "logistics/transport/cancellation",
            "name": "Booking Cancellation",
            "description": "Cancel an existing booking",
            "tags": ["cancellation", "refund"],
        },
    ],
    
    "authentication": {
        "schemes": ["bearer"],
    },
    
    "extensions": {
        "acp_interrupt_support": True,
        "requires_approval": True,
    },
}
