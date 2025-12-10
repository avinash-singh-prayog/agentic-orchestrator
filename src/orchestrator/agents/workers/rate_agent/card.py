"""
OASF Agent Card for the Rate Agent.
"""

from typing import Any

RATE_AGENT_CARD: dict[str, Any] = {
    "name": "rate-agent",
    "version": "1.0.0",
    "description": "Aggregates shipping rate quotes from multiple carriers using parallel queries",
    "url": "http://localhost:9002",
    
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
    },
    
    "skills": [
        {
            "id": "commerce/pricing/quote",
            "name": "Rate Quote",
            "description": "Get shipping rate quotes from carriers",
            "tags": ["pricing", "quotes", "carriers"],
        },
        {
            "id": "commerce/pricing/comparison",
            "name": "Rate Comparison",
            "description": "Compare rates across multiple carriers",
            "tags": ["comparison", "optimization"],
        },
    ],
    
    "authentication": {
        "schemes": ["bearer"],
    },
}
