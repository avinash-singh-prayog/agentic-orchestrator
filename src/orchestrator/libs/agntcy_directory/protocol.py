"""
Protocol/Interface definition for Directory Client implementations.

This module defines the abstract interface that all directory client
implementations must follow. Using Python's Protocol (structural subtyping)
allows for duck-typing while maintaining type safety.
"""

from typing import Protocol, List, Optional, Dict, Any, runtime_checkable
from .models import AgentRecord, RecordMeta, SearchQuery


@runtime_checkable
class DirectoryClientProtocol(Protocol):
    """
    Abstract protocol for Directory Service client implementations.
    
    All implementations (GrpcDirectoryClient, DirctlDirectoryClient, future SDK)
    must implement these methods. Using Protocol allows for structural subtyping,
    meaning any class with these methods will be considered compatible.
    
    Example:
        class MyCustomClient:
            def push(self, record: AgentRecord) -> str: ...
            def pull(self, cid: str) -> AgentRecord: ...
            # ... other methods
        
        # MyCustomClient is automatically a DirectoryClientProtocol
    """
    
    def push(self, record: AgentRecord) -> str:
        """
        Push (register) an agent record to the Directory Service.
        
        Args:
            record: The agent record to register
            
        Returns:
            CID (Content Identifier) of the registered record
            
        Raises:
            RegistrationError: If registration fails
            ConnectionError: If connection to service fails
        """
        ...
    
    def pull(self, cid: str) -> AgentRecord:
        """
        Pull (retrieve) a full agent record by its CID.
        
        Args:
            cid: Content Identifier of the record
            
        Returns:
            The full agent record
            
        Raises:
            RecordNotFoundError: If record not found
            ConnectionError: If connection to service fails
        """
        ...
    
    def search_cids(self, query: Optional[SearchQuery] = None) -> List[str]:
        """
        Search for agent CIDs matching the query.
        
        Args:
            query: Search filters (optional, None returns all)
            
        Returns:
            List of CIDs matching the query
            
        Raises:
            SearchError: If search fails
            ConnectionError: If connection to service fails
        """
        ...
    
    def search_records(self, query: Optional[SearchQuery] = None) -> List[AgentRecord]:
        """
        Search for full agent records matching the query.
        
        This is a convenience method that searches for CIDs and then
        pulls each record. For better performance, use search_cids()
        and pull records selectively.
        
        Args:
            query: Search filters (optional, None returns all)
            
        Returns:
            List of agent records matching the query
        """
        ...
    
    def delete(self, cid: str) -> bool:
        """
        Delete a record from the Directory Service.
        
        Args:
            cid: Content Identifier of the record to delete
            
        Returns:
            True if successfully deleted
            
        Raises:
            RecordNotFoundError: If record not found
            ConnectionError: If connection to service fails
        """
        ...
    
    def info(self, cid: str) -> RecordMeta:
        """
        Get metadata about a record without pulling the full content.
        
        Args:
            cid: Content Identifier of the record
            
        Returns:
            Record metadata (size, created_at, etc.)
            
        Raises:
            RecordNotFoundError: If record not found
            ConnectionError: If connection to service fails
        """
        ...
    
    def health_check(self) -> bool:
        """
        Check if the Directory Service is reachable and healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        ...
    
    # High-level convenience methods
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """
        Get all registered agents with their capabilities.
        
        Returns:
            List of dicts with agent name, description, and capabilities
        """
        ...
    
    def find_agent_by_capability(self, capability: str) -> Optional[AgentRecord]:
        """
        Find an agent that has the specified capability.
        
        Args:
            capability: The capability to search for (e.g., "rate_fetching")
            
        Returns:
            Agent record if found, None otherwise
        """
        ...
    
    def register_agent(self, record_path: str) -> Optional[str]:
        """
        Register an agent from a JSON file path.
        
        Args:
            record_path: Path to the agent_record.json file
            
        Returns:
            CID if successful, None otherwise
        """
        ...
