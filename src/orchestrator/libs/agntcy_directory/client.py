"""
Factory class for Directory Client.

Provides a unified interface that automatically selects the appropriate
client implementation based on environment detection.
"""

import os
import logging
from typing import Optional, List, Dict, Any, Union

from .models import AgentRecord, RecordMeta, SearchQuery, ConnectionConfig
from .protocol import DirectoryClientProtocol
from .grpc_client import GrpcDirectoryClient
from .dirctl_client import DirctlDirectoryClient
from .exceptions import DirectoryError

logger = logging.getLogger("agntcy_directory")


class DirectoryClient:
    """
    Factory class that provides a unified Directory Service client.
    
    Automatically selects the best implementation based on environment:
    - Uses DirctlDirectoryClient for local development (non-TLS)
    - Uses GrpcDirectoryClient for production (TLS on port 443)
    
    This is the recommended way to use the library, as it handles
    implementation selection transparently.
    
    Example:
        # Recommended: auto-detect from environment
        client = DirectoryClient.from_env()
        
        # Manual configuration
        config = ConnectionConfig(server_addr="dir.example.com:443", use_tls=True)
        client = DirectoryClient(config)
        
        # Use the client
        cid = client.register_agent("agent_record.json")
        agents = client.list_all_agents()
    """
    
    def __init__(
        self,
        config: Optional[ConnectionConfig] = None,
        implementation: Optional[str] = None
    ):
        """
        Initialize the Directory Client.
        
        Args:
            config: Connection configuration. If None, reads from environment.
            implementation: Force a specific implementation ('grpc' or 'dirctl').
                          If None, auto-selects based on environment.
        """
        self.config = config or ConnectionConfig.from_env()
        self._impl: DirectoryClientProtocol = self._create_implementation(implementation)
        
        logger.info(
            f"DirectoryClient initialized using {type(self._impl).__name__} "
            f"-> {self.config.server_addr}"
        )
    
    def _create_implementation(self, implementation: Optional[str]) -> DirectoryClientProtocol:
        """Select and create the appropriate implementation."""
        if implementation:
            if implementation.lower() == "grpc":
                return GrpcDirectoryClient(self.config)
            elif implementation.lower() == "dirctl":
                return DirctlDirectoryClient(self.config)
            else:
                raise ValueError(f"Unknown implementation: {implementation}")
        
        # Auto-select based on environment
        # For now, always use dirctl as it works for both local and has full implementation
        # GrpcDirectoryClient requires generated proto stubs
        use_impl = os.getenv("DIRECTORY_CLIENT_IMPL", "dirctl").lower()
        
        if use_impl == "grpc":
            logger.info("Using native gRPC implementation")
            return GrpcDirectoryClient(self.config)
        else:
            logger.info("Using dirctl subprocess implementation")
            return DirctlDirectoryClient(self.config)
    
    @classmethod
    def from_env(cls) -> "DirectoryClient":
        """
        Create a DirectoryClient from environment variables.
        
        Environment variables:
            DIRECTORY_SERVICE_ADDR: Server address (default: localhost:8888)
            DIRECTORY_CLIENT_IMPL: Implementation to use (grpc/dirctl, default: dirctl)
            DIRECTORY_TLS_SKIP_VERIFY: Skip TLS verification (default: false)
            DIRECTORY_TIMEOUT: Request timeout in seconds (default: 30)
        
        Returns:
            Configured DirectoryClient instance
        """
        return cls()
    
    # Delegate all operations to the implementation
    
    def push(self, record: AgentRecord) -> str:
        """Push an agent record to the Directory Service."""
        return self._impl.push(record)
    
    def pull(self, cid: str) -> AgentRecord:
        """Pull a record by CID."""
        return self._impl.pull(cid)
    
    def search_cids(self, query: Optional[SearchQuery] = None) -> List[str]:
        """Search for CIDs matching the query."""
        return self._impl.search_cids(query)
    
    def search_records(self, query: Optional[SearchQuery] = None) -> List[AgentRecord]:
        """Search for full records."""
        return self._impl.search_records(query)
    
    def delete(self, cid: str) -> bool:
        """Delete a record."""
        return self._impl.delete(cid)
    
    def info(self, cid: str) -> RecordMeta:
        """Get record metadata."""
        return self._impl.info(cid)
    
    def health_check(self) -> bool:
        """Check if the Directory Service is healthy."""
        return self._impl.health_check()
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """Get all registered agents with their capabilities."""
        return self._impl.list_all_agents()
    
    def find_agent_by_capability(self, capability: str) -> Optional[AgentRecord]:
        """Find an agent with the specified capability."""
        return self._impl.find_agent_by_capability(capability)
    
    def register_agent(self, record_path: str = "agent_record.json") -> Optional[str]:
        """Register an agent from a JSON file."""
        return self._impl.register_agent(record_path)
    
    # Context manager support
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self._impl, 'close'):
            self._impl.close()


# Convenience functions for quick access

def register_agent(record_path: str = "agent_record.json") -> Optional[str]:
    """
    Quick function to register an agent.
    
    Creates a DirectoryClient, registers the agent, and returns the CID.
    
    Args:
        record_path: Path to the agent_record.json file
        
    Returns:
        CID if successful, None otherwise
    """
    client = DirectoryClient.from_env()
    return client.register_agent(record_path)


def list_agents() -> List[Dict[str, Any]]:
    """
    Quick function to list all agents.
    
    Returns:
        List of agent info dicts with name, description, capabilities
    """
    client = DirectoryClient.from_env()
    return client.list_all_agents()


def find_by_capability(capability: str) -> Optional[AgentRecord]:
    """
    Quick function to find an agent by capability.
    
    Args:
        capability: The capability to search for
        
    Returns:
        AgentRecord if found, None otherwise
    """
    client = DirectoryClient.from_env()
    return client.find_agent_by_capability(capability)
