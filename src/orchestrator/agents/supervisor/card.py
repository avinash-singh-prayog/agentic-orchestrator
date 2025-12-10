"""
OASF Agent Card for the Orchestrator Supervisor

Defines the supervisor's identity, capabilities, and interface
following the Open Agent Schema Framework (OASF) specification.
"""

from typing import Any

SUPERVISOR_AGENT_CARD: dict[str, Any] = {
    "name": "orchestrator-supervisor",
    "version": "1.0.0",
    "description": "Multi-agent logistics orchestrator supervisor that coordinates order processing",
    "url": "http://localhost:8000",
    
    "capabilities": {
        "streaming": True,
        "pushNotifications": False,
        "stateTransitionHistory": True,
    },
    
    "skills": [
        {
            "id": "logistics/orchestration/order_processing",
            "name": "Order Processing",
            "description": "Process shipping orders through validation, quoting, and booking",
            "tags": ["logistics", "shipping", "orchestration"],
            "input": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Natural language order request"},
                    "order": {"type": "object", "description": "Structured order data"},
                },
            },
            "output": {
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "order_status": {"type": "string"},
                    "quotes": {"type": "array"},
                },
            },
        },
        {
            "id": "logistics/verification/serviceability_check",
            "name": "Serviceability Check",
            "description": "Check if a route is serviceable (delegates to Serviceability Agent)",
            "tags": ["validation", "shipping"],
        },
        {
            "id": "commerce/pricing/quote_request",
            "name": "Quote Request",
            "description": "Request shipping quotes from carriers (delegates to Rate Agent)",
            "tags": ["pricing", "quotes"],
        },
        {
            "id": "logistics/transport/booking",
            "name": "Booking",
            "description": "Book a shipment with a carrier (delegates to Carrier Agent, may require HITL)",
            "tags": ["booking", "transaction"],
        },
    ],
    
    "authentication": {
        "schemes": ["bearer"],
    },
    
    "extensions": {
        "acp_interrupt_support": True,
        "hitl_enabled": True,
        "max_auto_approval_limit": 5000,
    },
}


def get_agent_card() -> dict[str, Any]:
    """Get the supervisor agent card."""
    return SUPERVISOR_AGENT_CARD
