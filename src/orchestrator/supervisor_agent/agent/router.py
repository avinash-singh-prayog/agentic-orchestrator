"""
Discovery Router for AGNTCY IoA Architecture.

Implements TRUE DYNAMIC DISCOVERY:
- Supervisor queries Directory by capability (e.g., "rate_fetching")
- Directory returns agent record containing that capability
- Supervisor EXTRACTS SLIM topic from the record's DESCRIPTION field
- No guessing, no conventions - agent announces "how to talk to me"

Due to dir-apiserver v0.6.0 strict validation rejecting custom modules 
and protocol locator types, we use a robust "Description Hack":
The topic is embedded in the agent description as [TOPIC:domain.service.v1].
The capability is embedded as [CAPABILITY:rate_fetching].
"""
import os
import re
import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
)

from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from langchain_core.callbacks.manager import dispatch_custom_event
from agent.shared import get_factory
from agent.directory import DirectoryClient, AgentNotFoundError

logger = logging.getLogger("supervisor_agent.router")


def extract_topic_from_description(description: str) -> Optional[str]:
    """
    Extract SLIM topic from agent record's description string.
    
    Looks for pattern: [TOPIC:logistics.serviceability.v1]
    The regex is permissive to space around content inside brackets.
    """
    if not description:
        return None
        
    match = re.search(r'\[TOPIC:([a-zA-Z0-9._-]+)\]', description)
    if match:
        return match.group(1).strip()
    return None


class DiscoveryRouter:
    """
    Routes messages using TRUE DYNAMIC DISCOVERY.
    
    The Discovery Flow:
    1. Search Directory for capability string (e.g., "[CAPABILITY:rate_fetching]")
    2. Extract SLIM topic from agent's DESCRIPTION
    3. If no topic found, FAIL (agent must announce itself)
    4. Route via SLIM to the discovered topic
    """
    
    def __init__(self):
        self.directory = DirectoryClient()
        self.factory = get_factory()
        self.slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")
        self.supervisor_identity = "default/default/supervisor-agent"
        
        logger.info("DiscoveryRouter initialized - TRUE CAPABILITY DISCOVERY (No Hardcoding)")
    
    async def route_by_capability(self, capability: str, payload: str) -> str:
        """
        Route a message to an agent that has the specified capability.
        
        TRUE DISCOVERY:
        - Searches Directory for capability string tag
        - Extracts topic from description (agent announces itself)
        - No hardcoded mapping of capability -> agent name
        """
        # Phase 1: Search Directory for the capability tag
        # e.g., "rate_fetching" -> search for "[CAPABILITY:rate_fetching]"
        search_term = f"[CAPABILITY:{capability}]"
        
        # EMIT ACTIVITY EVENT: Directory Lookup Started
        dispatch_custom_event(
            "directory_lookup_start",
            {
                "capability": capability,
                "status": "searching",
                "message": f"🔍 [REST API] Querying Directory for capability: '{capability}'..."
            }
        )
        
        try:
            # We use find_agent_by_name because dirctl search works on full text
            # so searching for the tag will return the agent that has it in description
            agent = self.directory.find_agent_by_name(search_term)
            if not agent:
                # Try fallback: Just search the capability word (less precise but works if tag missing)
                logger.info(f"Tag search '{search_term}' failed, trying loose search '{capability}'")
                agent = self.directory.find_agent_by_name(capability)
                
            if not agent:
                raise AgentNotFoundError(f"No agent found with capability '{capability}'")

        except Exception as e:
            logger.error(f"Directory search failed: {e}")
            raise AgentNotFoundError(f"Directory search failed for capability '{capability}': {e}")
        
        # Phase 2: Extract topic from description (TRUE DISCOVERY)
        description = agent.get("description", "")
        agent_name = agent.get("name", "Unknown Agent")
        
        topic = extract_topic_from_description(description)
        
        if not topic:
            raise AgentNotFoundError(
                f"Agent '{agent_name}' found for capability '{capability}' has no [TOPIC:...] tag. "
                "Agent must register with topic in description."
            )
        
        logger.info(f"DISCOVERED: Agent '{agent_name}' handles '{capability}' -> topic '{topic}'")
        
        # EMIT ACTIVITY EVENT: Directory Lookup Success
        dispatch_custom_event(
            "directory_lookup_end",
            {
                "capability": capability,
                "agent_name": agent_name,
                "topic": topic,
                "status": "found",
                "message": f"✅ [REST API] Found: '{agent_name}' → SLIM topic '{topic}'"
            }
        )
        
        # Phase 3: Route via SLIM to discovered topic
        return await self._send_via_slim(topic, payload, agent_name)
    
    async def _send_via_slim(self, topic: str, payload: str, agent_name: str = "Agent") -> str:
        """Send message via SLIM Transporter to the specified topic."""
        
        logger.info(f"Creating SLIM transport to {self.slim_endpoint}")
        
        # EMIT EVENT: SLIM Transport starting
        dispatch_custom_event(
            "slim_routing_start",
            {
                "topic": topic,
                "message": f"📡 [SLIM A2A] Sending message to topic '{topic}'..."
            }
        )
        
        transport = self.factory.create_transport(
            "SLIM",
            endpoint=self.slim_endpoint,
            name=self.supervisor_identity
        )
        
        client = await self.factory.create_client(
            "A2A",
            agent_topic=topic,
            transport=transport
        )
        
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message=Message(
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(root=TextPart(text=payload))],
                )
            ),
        )
        
        logger.info(f"Sending message to topic '{topic}': {payload[:50]}...")
        
        try:
            response = await client.send_message(request)
            
            if response.root.result:
                if response.root.result.parts:
                    part = response.root.result.parts[0].root
                    if hasattr(part, "text"):
                        logger.info(f"Received response from topic '{topic}'")
                        
                        # EMIT EVENT: Agent responded via SLIM
                        dispatch_custom_event(
                            "agent_response",
                            {
                                "agent_name": agent_name,
                                "topic": topic,
                                "protocol": "SLIM A2A",
                                "message": f"[SLIM A2A] {agent_name} responded: {part.text[:150]}..."
                            }
                        )
                        
                        return part.text
            elif response.root.error:
                error_msg = f"A2A error: {response.root.error.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            return "No response from agent"
            
        except Exception as e:
            logger.error(f"Error sending to topic '{topic}': {e}")
            raise


# Singleton instance
_router: Optional[DiscoveryRouter] = None


def get_router() -> DiscoveryRouter:
    """Get or create the singleton DiscoveryRouter instance."""
    global _router
    if _router is None:
        _router = DiscoveryRouter()
    return _router


async def route_to_capability(capability: str, payload: str) -> str:
    """Convenience function to route a message by capability."""
    router = get_router()
    return await router.route_by_capability(capability, payload)
