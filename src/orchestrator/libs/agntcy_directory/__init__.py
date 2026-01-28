"""
AGNTCY Directory Client Library

A shared Python library for interacting with the AGNTCY Directory Service.
Supports both native gRPC (with TLS for production) and subprocess-based dirctl (for development).

Example usage:
    from libs.agntcy_directory import DirectoryClient, AgentRecord
    
    # Auto-detects environment and selects appropriate implementation
    client = DirectoryClient.from_env()
    
    # Register an agent
    cid = client.push(agent_record)
    
    # Search for agents
    cids = client.search_cids()
    
    # Pull full record
    record = client.pull(cid)
"""

from .models import AgentRecord, RecordMeta, SearchQuery, ConnectionConfig
from .protocol import DirectoryClientProtocol
from .client import DirectoryClient
from .grpc_client import GrpcDirectoryClient
from .dirctl_client import DirctlDirectoryClient
from .exceptions import (
    DirectoryError,
    ConnectionError,
    RecordNotFoundError,
    RegistrationError,
)

__all__ = [
    # Main client
    "DirectoryClient",
    # Implementations
    "GrpcDirectoryClient", 
    "DirctlDirectoryClient",
    # Protocol
    "DirectoryClientProtocol",
    # Models
    "AgentRecord",
    "RecordMeta",
    "SearchQuery", 
    "ConnectionConfig",
    # Exceptions
    "DirectoryError",
    "ConnectionError",
    "RecordNotFoundError",
    "RegistrationError",
]

__version__ = "0.1.0"
