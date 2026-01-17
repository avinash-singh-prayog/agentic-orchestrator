"""
Supervisor Agent Tools.

TRUE CAPABILITY-BASED DISCOVERY:
The Supervisor does NOT know about specific agents.
It discovers capabilities dynamically from the Directory Service.
"""
import logging
import json
from langchain_core.tools import tool
from langchain_core.callbacks.manager import dispatch_custom_event

from agent.router import route_to_capability
from agent.directory import DirectoryClient, AgentNotFoundError

logger = logging.getLogger("supervisor_agent.tools")


@tool
def discover_capabilities() -> str:
    """
    Query the Directory Service to discover all available agent capabilities.
    
    Use this tool FIRST when you need to know what capabilities are available
    in the system. Returns a list of registered agents and their capabilities.
    
    Returns:
        JSON string listing available agents with their capabilities.
    """
    logger.info("Discovering available capabilities from Directory Service...")
    
    dispatch_custom_event(
        "discovery_start",
        {"message": "🔍 Querying Directory Service for available agents..."}
    )
    
    try:
        client = DirectoryClient()
        agents = client.list_all_agents()
        
        if not agents:
            dispatch_custom_event(
                "discovery_end",
                {"status": "empty", "message": "⚠️ No agents registered in Directory"}
            )
            return json.dumps({"agents": [], "message": "No agents are currently registered in the Directory Service."})
        
        dispatch_custom_event(
            "discovery_end",
            {"status": "success", "count": len(agents), "message": f"✅ Found {len(agents)} registered agents"}
        )
        
        return json.dumps({"agents": agents}, indent=2)
        
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        dispatch_custom_event(
            "discovery_end",
            {"status": "error", "message": f"❌ Discovery failed: {str(e)[:100]}"}
        )
        return json.dumps({"error": str(e), "agents": []})


@tool
async def delegate_to_capability(capability: str, message: str) -> str:
    """
    Delegate a task to an agent that has the specified capability.
    
    This is the ONLY way to communicate with other agents. The Supervisor
    does NOT know which specific agent will handle the request - it discovers
    the agent dynamically from the Directory Service.
    
    IMPORTANT: If you don't know what capabilities exist, call discover_capabilities() first.
    
    Args:
        capability: The capability needed (discovered via discover_capabilities or from context)
        message: The complete, standalone request with ALL necessary details.
                 Must include all context (e.g., locations, weights, dates) because
                 the receiving agent is STATELESS and has no conversation history.
    
    Returns:
        The response from the discovered agent, or an error if no agent has that capability.
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


# Dynamic discovery tools - Supervisor discovers capabilities from Directory Service
SUPERVISOR_TOOLS = [discover_capabilities, delegate_to_capability]
