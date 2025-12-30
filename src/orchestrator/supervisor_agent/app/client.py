"""
Supervisor Agent Client.

Creates an A2A client to communicate with the Serviceability Agent via SLIM Transporter.
Uses dynamic discovery via Directory Service to find agent endpoints.
"""

import os
import logging
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
from agent.shared import get_factory

logger = logging.getLogger("supervisor_agent.client")

# Fallback topic if Directory Service is unavailable
SERVICEABILITY_AGENT_TOPIC_FALLBACK = "serviceability-agent"


async def call_serviceability_via_slim(prompt: str) -> str:
    """
    Call the Serviceability Agent via SLIM Transporter using A2A Protocol.
    
    Uses Directory Service for dynamic discovery. Falls back to static topic
    if agent is not registered or directory is unavailable.
    
    Args:
        prompt: The user's request to forward to the serviceability agent.
        
    Returns:
        The serviceability agent's response text.
    """
    factory = get_factory()
    
    slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")
    supervisor_identity = "default/default/supervisor-agent"
    
    logger.info(f"Creating SLIM transport to {slim_endpoint}")
    
    # Dynamic Service Discovery via Directory
    target_topic = SERVICEABILITY_AGENT_TOPIC_FALLBACK
    try:
        from agent.directory import DirectoryClient
        dir_client = DirectoryClient()
        discovered_topic = dir_client.get_agent_slim_topic("Serviceability Agent")
        
        if discovered_topic:
            target_topic = discovered_topic
            logger.info(f"Discovered Serviceability Agent SLIM topic: {target_topic}")
        else:
            logger.warning(f"Serviceability Agent not found in Directory. Using fallback topic: {target_topic}")
    except Exception as e:
        logger.warning(f"Directory lookup failed: {e}. Using fallback topic: {target_topic}")

    # Create transport for SLIM
    transport = factory.create_transport(
        "SLIM",
        endpoint=slim_endpoint,
        name=supervisor_identity
    )
    
    # Create A2A client targeting the discovered agent
    client = await factory.create_client(
        "A2A",
        agent_topic=target_topic,
        transport=transport
    )
    
    # Construct A2A message request
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message=Message(
                messageId=str(uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=prompt))],
            )
        ),
    )
    
    logger.info(f"Sending message to {target_topic}: {prompt[:50]}...")
    
    try:
        response = await client.send_message(request)
        
        # Extract response text per A2A protocol
        if response.root.result:
            if response.root.result.parts:
                part = response.root.result.parts[0].root
                if hasattr(part, "text"):
                    logger.info(f"Received response from serviceability agent")
                    return part.text
        elif response.root.error:
            error_msg = f"A2A error: {response.root.error.message}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return "No response from serviceability agent"
        
    except Exception as e:
        logger.error(f"Error calling serviceability agent: {e}")
        return f"Error communicating with serviceability agent: {e}"
