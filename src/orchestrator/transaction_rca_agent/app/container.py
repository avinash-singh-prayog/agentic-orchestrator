"""
Dependency Injection Container.

Wires together all dependencies for the transaction RCA agent.
"""

from agent.graph import TransactionRCAGraph


class Container:
    """Dependency injection container."""

    _graph: TransactionRCAGraph | None = None

    @classmethod
    def get_graph(cls) -> TransactionRCAGraph:
        """Get or create the transaction RCA graph."""
        if cls._graph is None:
            cls._graph = TransactionRCAGraph()
        return cls._graph

    @classmethod
    def reset(cls) -> None:
        """Reset all singletons (useful for testing)."""
        cls._graph = None
