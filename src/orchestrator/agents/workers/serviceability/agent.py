"""
Serviceability Agent

LangGraph-based agent for validating shipping routes.
Handles:
- Address validation
- Embargo/restriction checks
- Route availability
- Carrier coverage lookup
"""

import logging
from enum import Enum
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from orchestrator.common.llm import get_llm_provider

logger = logging.getLogger(__name__)


# Known embargo countries (for demo purposes)
EMBARGO_COUNTRIES = [
    "north korea", "iran", "syria", "cuba", "crimea"
]

# Serviceable regions (for demo purposes)
SERVICEABLE_REGIONS = {
    "fedex": ["us", "eu", "asia", "australia", "india", "canada"],
    "dhl": ["us", "eu", "asia", "middle_east", "africa", "india"],
    "ups": ["us", "eu", "asia", "canada", "mexico", "india"],
}


class NodeState(str, Enum):
    """Node states for the serviceability workflow."""
    
    VALIDATE_ADDRESS = "validate_address"
    CHECK_EMBARGO = "check_embargo"
    CHECK_ROUTE = "check_route"
    RESPONSE = "response"


class ServiceabilityState(TypedDict):
    """State for serviceability workflow."""
    
    origin: str
    destination: str
    shipment_type: str
    
    # Validation results
    origin_valid: bool | None
    destination_valid: bool | None
    embargo_clear: bool | None
    route_available: bool | None
    
    # Results
    is_serviceable: bool | None
    available_carriers: list[str]
    reasons: list[str]
    response: str


class ServiceabilityAgent:
    """
    Serviceability validation agent.
    
    Validates shipping routes through a multi-step workflow:
    1. Address validation
    2. Embargo/restriction check
    3. Route availability check
    """
    
    def __init__(self):
        """Initialize the serviceability agent."""
        self._llm = get_llm_provider(agent_type="serviceability")
        self._graph: CompiledStateGraph | None = None
        logger.info("Initialized ServiceabilityAgent")
    
    @property
    def graph(self) -> CompiledStateGraph:
        """Get or build the compiled graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph StateGraph."""
        builder = StateGraph(ServiceabilityState)
        
        # Add nodes
        builder.add_node(NodeState.VALIDATE_ADDRESS, self._validate_address_node)
        builder.add_node(NodeState.CHECK_EMBARGO, self._check_embargo_node)
        builder.add_node(NodeState.CHECK_ROUTE, self._check_route_node)
        builder.add_node(NodeState.RESPONSE, self._response_node)
        
        # Add edges
        builder.add_edge(START, NodeState.VALIDATE_ADDRESS)
        builder.add_edge(NodeState.VALIDATE_ADDRESS, NodeState.CHECK_EMBARGO)
        builder.add_edge(NodeState.CHECK_EMBARGO, NodeState.CHECK_ROUTE)
        builder.add_edge(NodeState.CHECK_ROUTE, NodeState.RESPONSE)
        builder.add_edge(NodeState.RESPONSE, END)
        
        return builder.compile()
    
    # ===========================
    # Node Implementations
    # ===========================
    
    async def _validate_address_node(self, state: ServiceabilityState) -> dict[str, Any]:
        """Validate origin and destination addresses."""
        logger.info(f"Validating addresses: {state['origin']} -> {state['destination']}")
        
        # Simple validation: check if addresses are non-empty
        origin_valid = bool(state["origin"] and len(state["origin"]) > 2)
        destination_valid = bool(state["destination"] and len(state["destination"]) > 2)
        
        reasons = []
        if not origin_valid:
            reasons.append("Invalid origin address")
        if not destination_valid:
            reasons.append("Invalid destination address")
        
        return {
            "origin_valid": origin_valid,
            "destination_valid": destination_valid,
            "reasons": reasons,
        }
    
    async def _check_embargo_node(self, state: ServiceabilityState) -> dict[str, Any]:
        """Check for trade embargoes and restrictions."""
        logger.info(f"Checking embargoes for: {state['destination']}")
        
        # Check destination against embargo list
        destination_lower = state["destination"].lower()
        
        is_embargoed = any(
            country in destination_lower
            for country in EMBARGO_COUNTRIES
        )
        
        reasons = list(state.get("reasons", []))
        if is_embargoed:
            reasons.append(f"Destination is under trade embargo/restrictions")
        
        return {
            "embargo_clear": not is_embargoed,
            "reasons": reasons,
        }
    
    async def _check_route_node(self, state: ServiceabilityState) -> dict[str, Any]:
        """Check route availability and carrier coverage."""
        logger.info(f"Checking route availability")
        
        # If previous checks failed, skip route check
        if not state.get("origin_valid") or not state.get("destination_valid"):
            return {
                "route_available": False,
                "available_carriers": [],
            }
        
        if not state.get("embargo_clear"):
            return {
                "route_available": False,
                "available_carriers": [],
            }
        
        # For demo, all routes are available if embargoes clear
        # In production, would check carrier APIs
        available_carriers = ["FedEx", "DHL", "UPS"]
        
        return {
            "route_available": True,
            "available_carriers": available_carriers,
        }
    
    async def _response_node(self, state: ServiceabilityState) -> dict[str, Any]:
        """Generate final response."""
        is_serviceable = (
            state.get("origin_valid", False) and
            state.get("destination_valid", False) and
            state.get("embargo_clear", False) and
            state.get("route_available", False)
        )
        
        if is_serviceable:
            carriers = state.get("available_carriers", [])
            response = (
                f"Route from {state['origin']} to {state['destination']} is serviceable. "
                f"Available carriers: {', '.join(carriers)}"
            )
        else:
            reasons = state.get("reasons", ["Unknown issue"])
            response = (
                f"Route from {state['origin']} to {state['destination']} is NOT serviceable. "
                f"Reasons: {', '.join(reasons)}"
            )
        
        return {
            "is_serviceable": is_serviceable,
            "response": response,
        }
    
    # ===========================
    # Public Interface
    # ===========================
    
    async def ainvoke(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke the serviceability check.
        
        Args:
            request: Dictionary with 'origin', 'destination', 'shipment_type'.
            
        Returns:
            Serviceability check results.
        """
        initial_state: ServiceabilityState = {
            "origin": request.get("origin", ""),
            "destination": request.get("destination", ""),
            "shipment_type": request.get("shipment_type", "standard"),
            "origin_valid": None,
            "destination_valid": None,
            "embargo_clear": None,
            "route_available": None,
            "is_serviceable": None,
            "available_carriers": [],
            "reasons": [],
            "response": "",
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "is_serviceable": result["is_serviceable"],
            "origin": result["origin"],
            "destination": result["destination"],
            "available_carriers": result["available_carriers"],
            "reasons": result["reasons"],
            "response": result["response"],
        }
