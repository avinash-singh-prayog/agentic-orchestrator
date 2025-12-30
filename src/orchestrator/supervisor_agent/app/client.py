"""
Supervisor Agent Client - Serviceability.

Uses capability-based discovery to route requests to agents
with "rate_fetching" capability via SLIM Transporter.
"""

import logging

from agent.router import route_to_capability
from agent.directory import AgentNotFoundError

logger = logging.getLogger("supervisor_agent.client")


async def call_serviceability_via_slim(prompt: str) -> str:
    """
    Call an agent with rate_fetching capability via SLIM Transporter.
    
    Uses IoA pattern:
    1. Discovers agent by "rate_fetching" capability
    2. Extracts SLIM topic from agent's extension_data
    3. Routes message via SLIM Transporter
    
    Args:
        prompt: The user's request to forward to the serviceability agent.
        
    Returns:
        The agent's response text.
        
    Raises:
        AgentNotFoundError: If no agent with rate_fetching capability exists.
    """
    logger.info(f"Routing request to agent with 'rate_fetching' capability")
    
    try:
        response = await route_to_capability("rate_fetching", prompt)
        return response
    except AgentNotFoundError as e:
        logger.error(f"Discovery failed: {e}")
        return f"Error: No agent available with rate fetching capability. Please ensure the Serviceability Agent is registered."
    except Exception as e:
        logger.error(f"Error during routing: {e}")
        return f"Error communicating with serviceability agent: {e}"
