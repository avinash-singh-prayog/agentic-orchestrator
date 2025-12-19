"""
Shared Factory Pattern.

Singleton AgntcyFactory for reuse across supervisor agent components.
"""

from typing import Optional
from agntcy_app_sdk.factory import AgntcyFactory

_factory: Optional[AgntcyFactory] = None


def set_factory(factory: AgntcyFactory) -> None:
    """Set the global factory instance."""
    global _factory
    _factory = factory


def get_factory() -> AgntcyFactory:
    """Get or create the factory instance."""
    if _factory is None:
        return AgntcyFactory("orchestrator.supervisor_agent", enable_tracing=False)
    return _factory
