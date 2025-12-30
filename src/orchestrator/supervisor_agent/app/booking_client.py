"""
Supervisor Agent Client - Booking.

Uses capability-based discovery to route requests to agents
with "order_creation" capability via SLIM Transporter.
"""

import logging

from agent.router import route_to_capability
from agent.directory import AgentNotFoundError

logger = logging.getLogger("supervisor_agent.booking_client")


async def call_booking_via_slim(prompt: str) -> str:
    """
    Call an agent with order_creation capability via SLIM Transporter.
    
    Uses IoA pattern:
    1. Discovers agent by "order_creation" capability
    2. Extracts SLIM topic from agent's extension_data
    3. Routes message via SLIM Transporter
    
    Args:
        prompt: The user's request to forward to the booking agent.
        
    Returns:
        The agent's response text.
        
    Raises:
        AgentNotFoundError: If no agent with order_creation capability exists.
    """
    logger.info(f"Routing request to agent with 'order_creation' capability")
    
    try:
        response = await route_to_capability("order_creation", prompt)
        return response
    except AgentNotFoundError as e:
        logger.error(f"Discovery failed: {e}")
        return f"Error: No agent available with order creation capability. Please ensure the Booking Agent is registered."
    except Exception as e:
        logger.error(f"Error during routing: {e}")
        return f"Error communicating with booking agent: {e}"
