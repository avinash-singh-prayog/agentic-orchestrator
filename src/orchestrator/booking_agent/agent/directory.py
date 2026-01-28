"""
Directory Client for Booking Agent.

Re-exports the shared DirectoryClient library for agent registration
and discovery operations.
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
    RecordMeta,
    SearchQuery,
    ConnectionConfig,
    DirectoryError,
    RecordNotFoundError,
    RegistrationError,
)

AgentNotFoundError = RecordNotFoundError
_client = None


def get_client() -> DirectoryClient:
    global _client
    if _client is None:
        _client = DirectoryClient.from_env()
    return _client


def register_agent(record_path: str = "agent_record.json") -> str | None:
    return get_client().register_agent(record_path)


def list_all_agents() -> list[dict]:
    return get_client().list_all_agents()


def find_agent_by_capability(capability: str) -> AgentRecord | None:
    return get_client().find_agent_by_capability(capability)


def get_routing_info(agent_name: str) -> dict | None:
    records = get_client().search_records()
    for record in records:
        if record.name == agent_name:
            routing = record.get_routing_module()
            if routing:
                return routing
    return None


__all__ = [
    "DirectoryClient", "AgentRecord", "RecordMeta", "SearchQuery",
    "ConnectionConfig", "DirectoryError", "RecordNotFoundError",
    "RegistrationError", "AgentNotFoundError", "get_client",
    "register_agent", "list_all_agents", "find_agent_by_capability",
    "get_routing_info",
]
