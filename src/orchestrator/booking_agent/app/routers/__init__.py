"""Routers initialization."""

from .health import router as health_router
from .agent import router as agent_router

__all__ = ["health_router", "agent_router"]
