"""
AGNTCY Factory

Factory for creating AGNTCY components: transports, clients, and sessions.
Based on the AgntcyFactory pattern from the Lungo reference project.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    """Container for an A2A application instance."""
    
    app: Any  # A2AStarletteApplication
    transport: Any  # Transport instance
    topic: str


class AgntcyFactory:
    """
    Factory for creating AGNTCY SDK components.
    
    Provides methods for creating:
    - Transport connections (SLIM)
    - A2A clients for inter-agent communication
    - App sessions for managing multiple agent containers
    
    Example:
        factory = AgntcyFactory("orchestrator.supervisor", enable_tracing=True)
        transport = factory.create_transport("SLIM", "http://localhost:46357")
        client = factory.create_client("a2a", "rate-agent-topic", transport)
    """
    
    def __init__(self, name: str, enable_tracing: bool = True):
        """
        Initialize the factory.
        
        Args:
            name: Application name for identification and tracing.
            enable_tracing: Whether to enable OpenTelemetry tracing.
        """
        self.name = name
        self.enable_tracing = enable_tracing
        logger.info(f"Initialized AgntcyFactory: {name} (tracing={enable_tracing})")
    
    def create_transport(
        self,
        transport_type: str,
        endpoint: str,
        name: str | None = None,
    ) -> Any:
        """
        Create a transport connection.
        
        Args:
            transport_type: Type of transport ("SLIM" or "NATS").
            endpoint: Server endpoint URL.
            name: Optional transport name.
            
        Returns:
            Transport instance.
            
        Note:
            For V1, this returns a placeholder. Full SLIM integration
            will be added when agntcy-slim-transport package is available.
        """
        transport_name = name or f"{self.name}.transport"
        logger.info(f"Creating {transport_type} transport: {transport_name} -> {endpoint}")
        
        # Placeholder for SLIM transport
        # In production, this would use:
        # from agntcy_slim import SLIMTransport
        # return SLIMTransport(endpoint)
        
        return {
            "type": transport_type,
            "endpoint": endpoint,
            "name": transport_name,
        }
    
    def create_client(
        self,
        protocol: str,
        agent_topic: str,
        transport: Any,
    ) -> Any:
        """
        Create an A2A client for agent communication.
        
        Args:
            protocol: Communication protocol ("a2a").
            agent_topic: Target agent's topic/address.
            transport: Transport instance.
            
        Returns:
            A2A client instance.
        """
        logger.info(f"Creating {protocol} client for topic: {agent_topic}")
        
        # Placeholder for A2A client
        # In production, this would use the AGNTCY App SDK
        
        return {
            "protocol": protocol,
            "topic": agent_topic,
            "transport": transport,
        }
    
    def create_app_session(self, max_sessions: int = 10) -> "AppSession":
        """
        Create an application session for managing agent containers.
        
        Args:
            max_sessions: Maximum number of concurrent sessions.
            
        Returns:
            AppSession instance.
        """
        return AppSession(factory=self, max_sessions=max_sessions)


class AppSession:
    """
    Manages multiple A2A application containers.
    
    Provides lifecycle management for agent services including
    starting, stopping, and health monitoring.
    """
    
    def __init__(self, factory: AgntcyFactory, max_sessions: int = 10):
        """
        Initialize the session manager.
        
        Args:
            factory: Parent AgntcyFactory instance.
            max_sessions: Maximum number of concurrent sessions.
        """
        self.factory = factory
        self.max_sessions = max_sessions
        self._containers: dict[str, AppContainer] = {}
    
    def add_app_container(self, name: str, container: AppContainer) -> None:
        """
        Add an application container to the session.
        
        Args:
            name: Container identifier.
            container: AppContainer instance.
        """
        self._containers[name] = container
        logger.info(f"Added container: {name}")
    
    async def start_session(self, name: str, keep_alive: bool = True) -> None:
        """
        Start a specific session.
        
        Args:
            name: Container name to start.
            keep_alive: Whether to keep the connection alive.
        """
        container = self._containers.get(name)
        if container:
            logger.info(f"Starting session: {name}")
            # In production, would start the A2A server
    
    async def stop_all_sessions(self) -> None:
        """Stop all running sessions."""
        for name in self._containers:
            logger.info(f"Stopping session: {name}")
        self._containers.clear()
