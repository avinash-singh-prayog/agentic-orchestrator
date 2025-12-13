"""
Dependency Injection Container.

Wires together all dependencies for the carrier service.
"""

from orchestrator.carrier_service.agent.graph import CarrierGraph
from orchestrator.carrier_service.infra.factory import CarrierFactory


class Container:
    """
    Dependency injection container.

    Provides singleton instances of service dependencies.
    """

    _factory: CarrierFactory | None = None
    _graph: CarrierGraph | None = None

    @classmethod
    def get_factory(cls) -> CarrierFactory:
        """Get or create the carrier factory."""
        if cls._factory is None:
            cls._factory = CarrierFactory()
        return cls._factory

    @classmethod
    def get_graph(cls) -> CarrierGraph:
        """Get or create the carrier graph."""
        if cls._graph is None:
            cls._graph = CarrierGraph(factory=cls.get_factory())
        return cls._graph

    @classmethod
    def reset(cls) -> None:
        """Reset all singletons (useful for testing)."""
        cls._factory = None
        cls._graph = None
