"""
Supervisor Agent Tools.

TRUE CAPABILITY-BASED DISCOVERY:
The Supervisor does NOT know about specific agents.
It only knows about CAPABILITIES and delegates to whatever agent has that capability.
"""
import logging
from langchain_core.tools import tool
from langchain_core.callbacks.manager import dispatch_custom_event

from agent.router import route_to_capability
from agent.directory import AgentNotFoundError

logger = logging.getLogger("supervisor_agent.tools")


@tool
async def delegate_to_capability(capability: str, message: str) -> str:
    """
    Delegate a task to an agent that has the specified capability.
    
    This is the ONLY way to communicate with other agents. The Supervisor
    does NOT know which specific agent will handle the request - it only
    knows about capabilities.
    
    Available capabilities:
    - "rate_fetching": Check shipping rates, serviceability, carrier availability
    - "route_validation": Validate shipping routes and coverage
    - "order_creation": Create new shipping orders/bookings
    - "order_tracking": Track existing orders
    - "order_cancellation": Cancel orders
    - "weather_forecast": Get multi-day weather forecast for a location
    - "location_weather": Get current weather conditions for a location
    - "web_search": Search the web for information on any topic
    - "content_extraction": Extract and summarize content from URLs
    - "personal_assistant": Personal assistance, weather, web search, productivity
    
    Args:
        capability: The capability needed (e.g., "rate_fetching", "order_creation")
        message: The complete, standalone request with ALL necessary details.
                 Must include all context (origin, destination, weight, partner_code, etc.)
                 because the receiving agent is STATELESS.
    
    Returns:
        The response from the discovered agent.
    
    Examples:
        - delegate_to_capability("rate_fetching", "Check rates from 713333 to 10003 for 5kg")
        - delegate_to_capability("order_creation", "Create order with partner_code=smile_hubops, origin=713333, dest=10003, weight=5kg")
    """
    logger.info(f"Supervisor delegating capability '{capability}' with message: {message[:50]}...")
    
    # Emit event: Capability routing started
    dispatch_custom_event(
        "capability_routing_start",
        {
            "capability": capability,
            "message": f"🎯 Routing by capability: '{capability}'..."
        }
    )
    
    try:
        # This does the Directory lookup + SLIM routing internally
        response = await route_to_capability(capability, message)
        
        # Emit event: Capability routing completed
        dispatch_custom_event(
            "capability_routing_end",
            {
                "capability": capability,
                "status": "success",
                "message": f"✅ Capability '{capability}' handled successfully"
            }
        )
        
        return response
        
    except AgentNotFoundError as e:
        logger.error(f"No agent found for capability '{capability}': {e}")
        
        dispatch_custom_event(
            "capability_routing_end",
            {
                "capability": capability,
                "status": "error",
                "message": f"❌ No agent found with capability '{capability}'"
            }
        )
        
        return f"Error: No agent available with '{capability}' capability. Please ensure an agent with this capability is registered in the Directory Service."
        
    except Exception as e:
        logger.error(f"Error during capability routing: {e}")
        
        dispatch_custom_event(
            "capability_routing_end",
            {
                "capability": capability,
                "status": "error", 
                "message": f"❌ Error routing to capability '{capability}': {str(e)[:100]}"
            }
        )
        
        return f"Error communicating with agent: {e}"


# Only ONE tool - the Supervisor doesn't know about specific agents
SUPERVISOR_TOOLS = [delegate_to_capability]
