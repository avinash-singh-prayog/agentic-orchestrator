"""
Directory Client for Personal Assistant Agent.

Re-exports the shared DirectoryClient library for agent registration.
"""

import sys
from pathlib import Path

# Add libs directory to path for import
def _setup_libs_path():
    docker_libs = Path("/app/libs")
    if docker_libs.exists():
        if str(docker_libs) not in sys.path:
            sys.path.insert(0, str(docker_libs))
        return
    local_libs = Path(__file__).parent.parent.parent / "libs"
    if local_libs.exists() and str(local_libs) not in sys.path:
        sys.path.insert(0, str(local_libs))

_setup_libs_path()

from agntcy_directory import (
    DirectoryClient,
    AgentRecord,
    DirectoryError,
    RegistrationError,
)

_client = None


def get_client() -> DirectoryClient:
    global _client
    if _client is None:
        _client = DirectoryClient.from_env()
    return _client


def register_agent(record_path: str = "agent_record.json") -> bool:
    try:
        cid = get_client().register_agent(record_path)
        return cid is not None
    except Exception:
        return False


__all__ = [
    "DirectoryClient", "AgentRecord", "DirectoryError",
    "RegistrationError", "get_client", "register_agent",
]
