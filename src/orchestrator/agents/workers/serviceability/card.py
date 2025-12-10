"""
OASF Agent Card for the Serviceability Agent.
"""

from typing import Any

SERVICEABILITY_AGENT_CARD: dict[str, Any] = {
    "name": "serviceability-agent",
    "version": "1.0.0",
    "description": "Validates shipping routes for serviceability, including address validation and embargo checks",
    "url": "http://localhost:9001",
    
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
    },
    
    "skills": [
        {
            "id": "logistics/verification/address_validation",
            "name": "Address Validation",
            "description": "Validate origin and destination addresses",
            "tags": ["validation", "address"],
        },
        {
            "id": "logistics/verification/embargo_check",
            "name": "Embargo Check",
            "description": "Check for trade restrictions and embargoes",
            "tags": ["compliance", "restrictions"],
        },
        {
            "id": "logistics/verification/route_availability",
            "name": "Route Availability",
            "description": "Check if shipping route is available",
            "tags": ["routing", "availability"],
        },
    ],
    
    "authentication": {
        "schemes": ["bearer"],
    },
}
