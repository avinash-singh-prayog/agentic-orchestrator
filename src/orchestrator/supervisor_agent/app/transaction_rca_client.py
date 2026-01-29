"""
Supervisor Agent Transaction RCA Client.

Creates an A2A client to communicate with the Transaction RCA Agent via SLIM Transporter.
Uses message-based A2A pattern per the multi_agent_architecture_guide.
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

logger = logging.getLogger("supervisor_agent.transaction_rca_client")

# Target agent topic (matches TransactionRCAAgentCard.id)
TRANSACTION_RCA_AGENT_TOPIC = "transaction-rca-agent"


async def call_transaction_rca_via_slim(transaction_context_json: str) -> str:
    """
    Call the Transaction RCA Agent via SLIM Transporter using A2A Protocol.
    
    Args:
        transaction_context_json: JSON string containing the transaction context.
        
    Returns:
        The transaction RCA agent's response text with RCA analysis.
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
    
    # Create A2A client targeting the transaction RCA agent
    client = await factory.create_client(
        "A2A",
        agent_topic=TRANSACTION_RCA_AGENT_TOPIC,
        transport=transport
    )
    
    # Construct A2A message request
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message=Message(
                messageId=str(uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=transaction_context_json))],
            )
        ),
    )
    
    logger.info(f"Sending message to {TRANSACTION_RCA_AGENT_TOPIC}: {transaction_context_json[:50]}...")
    
    try:
        response = await client.send_message(request)
        
        # Extract response text per A2A protocol
        if response.root.result:
            if response.root.result.parts:
                part = response.root.result.parts[0].root
                if hasattr(part, "text"):
                    logger.info(f"Received response from transaction RCA agent")
                    return part.text
        elif response.root.error:
            error_msg = f"A2A error: {response.root.error.message}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return "No response from transaction RCA agent"
        
    except Exception as e:
        logger.error(f"Error calling transaction RCA agent: {e}")
        return f"Error communicating with transaction RCA agent: {e}"
