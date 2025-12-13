"""
Dependency Injection Container.

Wires together all dependencies for the carrier service.
"""

from orchestrator.carrier_service.agent.graph import CarrierGraph
from orchestrator.carrier_service.services.carriers.factory import CarrierFactory
from orchestrator.carrier_service.services.carrier_orchestrator import CarrierOrchestrator
from orchestrator.carrier_service.services.carrier_selector import CarrierSelector
from orchestrator.carrier_service.agent import tools as agent_tools


class Container:
    """Dependency injection container."""

    _factory: CarrierFactory | None = None
    _selector: CarrierSelector | None = None
    _orchestrator: CarrierOrchestrator | None = None
    _graph: CarrierGraph | None = None

    @classmethod
    def get_factory(cls) -> CarrierFactory:
        """Get or create the carrier factory."""
        if cls._factory is None:
            cls._factory = CarrierFactory()
        return cls._factory

    @classmethod
    def get_selector(cls) -> CarrierSelector:
        """Get or create the carrier selector."""
        if cls._selector is None:
            cls._selector = CarrierSelector()
        return cls._selector

    @classmethod
    def get_orchestrator(cls) -> CarrierOrchestrator:
        """Get or create the carrier orchestrator."""
        if cls._orchestrator is None:
            cls._orchestrator = CarrierOrchestrator(
                factory=cls.get_factory(),
                selector=cls.get_selector(),
            )
            # Inject orchestrator into tools module
            agent_tools.set_orchestrator(cls._orchestrator)
        return cls._orchestrator

    @classmethod
    def get_graph(cls) -> CarrierGraph:
        """Get or create the carrier graph."""
        if cls._graph is None:
            # Ensure orchestrator is initialized first (injects into tools)
            cls.get_orchestrator()
            cls._graph = CarrierGraph()
        return cls._graph

    @classmethod
    def reset(cls) -> None:
        """Reset all singletons (useful for testing)."""
        cls._factory = None
        cls._selector = None
        cls._orchestrator = None
        cls._graph = None
