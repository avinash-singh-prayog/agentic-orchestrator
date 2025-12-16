"""
Carrier Agent A2A Server Wrapper.

Uses AgntcyFactory transport pattern with AppContainer for SLIM communication.
Follows the multi_agent_architecture_guide.md specifications.
"""

import os
import logging
import asyncio
from uuid import uuid4

# A2A Imports
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Role, Part, TextPart
from a2a.utils import new_agent_text_message, new_task

# AGNTCY SDK Imports
from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from agntcy_app_sdk.app_sessions import AppContainer

# Internal Imports
from ..domain.card import CarrierAgentCard
from .container import Container

logger = logging.getLogger("carrier_agent.server")

# Initialize factory with tracing
factory = AgntcyFactory("orchestrator.carrier_agent", enable_tracing=True)


class CarrierAgentExecutor(AgentExecutor):
    """
    Message-based executor following guide pattern.
    
    Adapts the internal LangGraph application to the A2A AgentExecutor interface.
    """
    
    def __init__(self):
        self.graph = Container.get_graph()
        self.agent_card = CarrierAgentCard.model_dump(mode="json", exclude_none=True)
    
    def _validate_request(self, context: RequestContext) -> bool:
        """Validate the incoming request context."""
        if not context or not context.message or not context.message.parts:
            return False
        return True
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute the agent task and push response to event queue.
        
        Args:
            context: The request context containing the user message.
            event_queue: Queue to push response events to.
        """
        if not self._validate_request(context):
            logger.error("Invalid request context")
            return
        
        # Extract user input from the message
        prompt = context.get_user_input()
        logger.info(f"Executing carrier agent with prompt: {prompt[:100]}...")
        
        # Ensure we have a task
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        
        try:
            # Invoke the internal LangGraph workflow
            result = await self.graph.invoke(prompt)
            
            # Extract the response message
            msgs = result.get("messages", [])
            output = "No response generated"
            if msgs:
                last_msg = msgs[-1]
                output = getattr(last_msg, 'content', str(last_msg))
            
            logger.info(f"Generated response: {output[:100]}...")
            
            # Create A2A response message
            message = Message(
                messageId=str(uuid4()),
                role=Role.agent,
                metadata={"name": self.agent_card.get("name", "Carrier Agent")},
                parts=[Part(root=TextPart(text=output))],
            )
            
            await event_queue.enqueue_event(message)
            
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            # Send error message
            error_message = Message(
                messageId=str(uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(text=f"Error processing request: {str(e)}"))],
            )
            await event_queue.enqueue_event(error_message)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation."""
        logger.info(f"Cancelling task for context: {context}")
        pass


async def run_server():
    """
    Run the Carrier Agent using SLIM transport pattern.
    
    This follows the guide's AppContainer + AppSession pattern for SLIM communication.
    """
    logger.info("Initializing Carrier Agent server...")
    
    # 1. Create task store and executor
    task_store = InMemoryTaskStore()
    executor = CarrierAgentExecutor()
    
    # 2. Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )
    
    # 3. Create A2A application
    server = A2AStarletteApplication(
        agent_card=CarrierAgentCard,
        http_handler=request_handler
    )
    
    # 4. Create SLIM transport
    slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")
    # Use explicit topic matching supervisor client's CARRIER_AGENT_TOPIC
    personal_topic = "carrier-agent"  # Matches the id from AgentCard
    
    logger.info(f"Creating SLIM transport to {slim_endpoint} with topic: {personal_topic}")
    
    transport = factory.create_transport(
        "SLIM",
        endpoint=slim_endpoint,
        name=f"default/default/{personal_topic}"
    )
    
    # 5. Create app session for SLIM communication
    app_session = factory.create_app_session(max_sessions=1)
    app_session.add_app_container("group_session", AppContainer(
        server,
        transport=transport
    ))
    
    # 6. Start session (blocking with keep_alive)
    logger.info(f"Starting carrier agent on SLIM with topic: {personal_topic}")
    await app_session.start_session("group_session", keep_alive=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_server())
