"""API Routers for Carrier Service."""

from orchestrator.carrier_service.app.routers.health import router as health_router
from orchestrator.carrier_service.app.routers.agent import router as agent_router
from orchestrator.carrier_service.app.routers.serviceability import router as serviceability_router

__all__ = ["health_router", "agent_router", "serviceability_router"]
