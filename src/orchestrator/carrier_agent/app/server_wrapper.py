"""
Carrier Agent SlimRPC Server Wrapper.

This module initializes the Carrier Agent as a SlimRPC server.
It exposes a simple 'chat' RPC method to interact with the agent.
"""

import os
import logging
import asyncio
import slimrpc
from slimrpc import Server
from slimrpc import unary_unary_rpc_method_handler

from .container import Container

logger = logging.getLogger("carrier_agent.server")

class CarrierAgentExecutor:
    """Executor that adapts the LangGraph workflow."""
    
    def __init__(self):
        self.graph = Container.get_graph()

    async def invoke(self, message: str) -> str:
        """Invoke the agent with a message."""
        logger.info(f"CarrierAgentExecutor received: {message}")
        result = await self.graph.invoke(message)
        
        # Extract response
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return "No response generated."

executor = CarrierAgentExecutor()

async def chat_handler(request: bytes, context) -> bytes:
    """
    Handle chat requests.
    Request/Response are raw bytes for simplicity in this fallback implementation.
    """
    try:
        prompt = request.decode("utf-8")
        logger.info(f"Received chat request: {prompt}")
        response = await executor.invoke(prompt)
        return response.encode("utf-8")
    except Exception as e:
        logger.error(f"Error handling chat: {e}")
        return f"Error: {e}".encode("utf-8")

async def run_slim_server():
    """Run the Carrier Agent as a SlimRPC server."""
    
    slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")
    local_name = "prayog/orchestrator/carrier-agent"
    
    # Configure SLIM
    from slimrpc.common import SLIMAppConfig
    config = SLIMAppConfig(
        identity=local_name,
        slim_client_config={
            "endpoint": slim_endpoint,
            "tls": {"insecure": True}
        },
        shared_secret="a" * 32
    )

    # Note: If SLIMAppConfig constructor signature is different, we might fail.
    # But let's try to infer from 'Server' help which showed 'from_slim_app_config'.
    # If SLIMAppConfig is hard to instantiate, we can use Server constructor with 'local_app'.
    # But 'local_app' is 'slim_bindings.slim.Slim'.
    # It's better to use 'from_slim_app_config' if possible, or build manually.
    
    # SIMPLER APPROACH based on recent successful 'imports':
    # We saw 'Server' takes 'local_app'.
    # We also saw 'SLIMAppConfig' in slimrpc.common (from dir list).
    
    # Let's try to construct Server using the helper which likely handles the Slim binding setup.
    server = await Server.from_slim_app_config(config)

    # Register RPC
    # Service name: "carrier-agent" (or can be any string, but client must match)
    # Method name: "chat"
    handler = unary_unary_rpc_method_handler(chat_handler)
    server.register_rpc("carrier-agent", "chat", handler)

    logger.info(f"Starting SlimRPC Server for Carrier Agent on {slim_endpoint}...")
    await server.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_slim_server())
