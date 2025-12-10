"""
Serviceability Agent Executor

A2A-compatible executor that wraps the ServiceabilityAgent
following the AgentExecutor interface pattern.
"""

import logging
from typing import Any

from orchestrator.agents.workers.serviceability.agent import ServiceabilityAgent
from orchestrator.agents.workers.serviceability.card import SERVICEABILITY_AGENT_CARD

logger = logging.getLogger(__name__)


class ServiceabilityAgentExecutor:
    """
    A2A-compatible executor for the Serviceability Agent.
    
    Implements the AgentExecutor interface pattern for
    integration with the AGNTCY A2A protocol.
    """
    
    def __init__(self):
        """Initialize the executor."""
        self.agent = ServiceabilityAgent()
        self.agent_card = SERVICEABILITY_AGENT_CARD
        logger.info("Initialized ServiceabilityAgentExecutor")
    
    async def execute(
        self,
        context: Any,  # RequestContext in production
        event_queue: Any = None,  # EventQueue in production
    ) -> dict[str, Any]:
        """
        Execute a serviceability check request.
        
        Args:
            context: Request context containing the message.
            event_queue: Optional event queue for async events.
            
        Returns:
            Response dictionary.
        """
        # Extract request from context
        # In production, would parse A2A message format
        if hasattr(context, "message"):
            request = self._parse_message(context.message)
        elif isinstance(context, dict):
            request = context
        else:
            request = {"origin": "", "destination": ""}
        
        # Validate request
        validation_error = self._validate_request(request)
        if validation_error:
            return {
                "status": "error",
                "error": validation_error,
            }
        
        # Execute agent
        try:
            result = await self.agent.ainvoke(request)
            
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def cancel(
        self,
        context: Any,
        event_queue: Any = None,
    ) -> dict[str, Any]:
        """
        Cancel a running request.
        
        Args:
            context: Request context.
            event_queue: Optional event queue.
            
        Returns:
            Cancellation result.
        """
        logger.info("Cancellation requested")
        return {"status": "cancelled"}
    
    def _parse_message(self, message: Any) -> dict[str, Any]:
        """Parse an A2A message into request parameters."""
        # In production, would parse JSON-RPC message
        if hasattr(message, "parts"):
            # Extract from message parts
            for part in message.parts:
                if hasattr(part, "content"):
                    # Try to parse as JSON
                    import json
                    try:
                        return json.loads(part.content)
                    except json.JSONDecodeError:
                        pass
        
        return {}
    
    def _validate_request(self, request: dict[str, Any]) -> str | None:
        """Validate request parameters."""
        if not request.get("origin"):
            return "Missing required field: origin"
        if not request.get("destination"):
            return "Missing required field: destination"
        return None
