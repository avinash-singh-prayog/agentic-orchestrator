"""
Booking Agent Dependency Container.

Manages shared resources and graph instance.
"""

from typing import Optional
from agent.graph import BookingGraph


class Container:
    """Dependency injection container for the booking agent."""

    _graph: Optional[BookingGraph] = None

    @classmethod
    def get_graph(cls) -> BookingGraph:
        """Get or create the BookingGraph instance."""
        if cls._graph is None:
            cls._graph = BookingGraph()
        return cls._graph

    @classmethod
    def reset(cls) -> None:
        """Reset the container (useful for testing)."""
        cls._graph = None
