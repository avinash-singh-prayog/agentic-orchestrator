"""
Dependency Injection Container.

Wires together all dependencies for the carrier service.
"""

from ..agent.graph import CarrierGraph
from ..services.serviceability.client import ServiceabilityClient
from ..agent import tools as agent_tools


class Container:
    """Dependency injection container."""

    _serviceability_client: ServiceabilityClient | None = None
    _graph: CarrierGraph | None = None

    @classmethod
    def get_serviceability_client(cls) -> ServiceabilityClient:
        """Get or create the serviceability client."""
        if cls._serviceability_client is None:
            cls._serviceability_client = ServiceabilityClient()
        return cls._serviceability_client

    @classmethod
    def get_graph(cls) -> CarrierGraph:
        """Get or create the carrier graph."""
        if cls._graph is None:
            cls._graph = CarrierGraph()
        return cls._graph

    @classmethod
    def reset(cls) -> None:
        """Reset all singletons (useful for testing)."""
        cls._serviceability_client = None
        cls._graph = None
