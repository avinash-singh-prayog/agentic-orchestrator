"""
Supervisor Agent Booking Client.

Creates an A2A client to communicate with the Booking Agent via SLIM Transporter.
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

logger = logging.getLogger("supervisor_agent.booking_client")

# Target agent topic (matches BookingAgentCard.id)
BOOKING_AGENT_TOPIC = "booking-agent"


async def call_booking_via_slim(prompt: str) -> str:
    """
    Call the Booking Agent via SLIM Transporter using A2A Protocol.
    
    Args:
        prompt: The user's request to forward to the booking agent.
        
    Returns:
        The booking agent's response text.
    """
    factory = get_factory()
    
    slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")
    supervisor_identity = "default/default/supervisor-agent"
    
    logger.info(f"Creating SLIM transport to {slim_endpoint}")
    
    # Create transport for SLIM
    transport = factory.create_transport(
        "SLIM",
        endpoint=slim_endpoint,
        name=supervisor_identity
    )
    
    # Create A2A client targeting the booking agent
    client = await factory.create_client(
        "A2A",
        agent_topic=BOOKING_AGENT_TOPIC,
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
    
    logger.info(f"Sending message to {BOOKING_AGENT_TOPIC}: {prompt[:50]}...")
    
    try:
        response = await client.send_message(request)
        
        # Extract response text per A2A protocol
        if response.root.result:
            if response.root.result.parts:
                part = response.root.result.parts[0].root
                if hasattr(part, "text"):
                    logger.info(f"Received response from booking agent")
                    return part.text
        elif response.root.error:
            error_msg = f"A2A error: {response.root.error.message}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return "No response from booking agent"
        
    except Exception as e:
        logger.error(f"Error calling booking agent: {e}")
        return f"Error communicating with booking agent: {e}"
