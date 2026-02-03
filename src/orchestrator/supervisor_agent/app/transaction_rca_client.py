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


async def call_transaction_rca_via_slim(
    transaction_context_json: str,
    llm_config: dict = None
) -> str:
    """
    Call the Transaction RCA Agent via SLIM Transporter using A2A Protocol.
    
    Args:
        transaction_context_json: JSON string containing the transaction context.
        llm_config: Optional dict with {"provider": "openai", "model": "gpt-4", "api_key": "sk-..."}
                    If provided, will be passed to the agent via message metadata.
        
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
    
    # Build message metadata with LLM config if provided
    message_metadata = {}
    if llm_config:
        message_metadata["llm_config"] = llm_config
        logger.info(f"Passing LLM config to Transaction RCA Agent: {llm_config.get('provider')}/{llm_config.get('model')}")
    
    # Construct A2A message request
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message=Message(
                messageId=str(uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=transaction_context_json))],
                metadata=message_metadata if message_metadata else None,
            )
        ),
    )
    
    logger.info(f"Sending message to {TRANSACTION_RCA_AGENT_TOPIC}: {transaction_context_json[:50]}...")
    
    try:
        response = await client.send_message(request)
        
        # Handle None response
        if response is None:
            error_msg = "Received None response from transaction RCA agent"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        
        # Handle missing root
        if not hasattr(response, 'root') or response.root is None:
            error_msg = "Response missing root attribute"
            logger.error(f"{error_msg}. Response type: {type(response)}, Response: {response}")
            return f"Error: {error_msg}"
        
        # Extract response text per A2A protocol
        if hasattr(response.root, 'result') and response.root.result:
            if hasattr(response.root.result, 'parts') and response.root.result.parts:
                part = response.root.result.parts[0]
                if hasattr(part, 'root') and part.root:
                    if hasattr(part.root, "text"):
                        logger.info(f"Received response from transaction RCA agent")
                        return part.root.text
                    else:
                        logger.warning(f"Part root missing text attribute. Part root type: {type(part.root)}")
                else:
                    logger.warning(f"Part missing root attribute. Part type: {type(part)}")
            else:
                logger.warning(f"Result missing parts. Result: {response.root.result}")
        elif hasattr(response.root, 'error') and response.root.error:
            error_msg = f"A2A error: {response.root.error.message if hasattr(response.root.error, 'message') else str(response.root.error)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        else:
            logger.warning(f"Response has no result or error. Root attributes: {dir(response.root)}")
        
        return "No response from transaction RCA agent"
        
    except AttributeError as e:
        error_msg = f"Attribute error while parsing response: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"
    except Exception as e:
        logger.error(f"Error calling transaction RCA agent: {e}", exc_info=True)
        return f"Error communicating with transaction RCA agent: {str(e)}"
