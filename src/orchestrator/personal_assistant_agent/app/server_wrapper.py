"""
Personal Assistant Agent A2A Server Wrapper.

Uses AgntcyFactory transport pattern with AppContainer for SLIM communication.
"""
import os
import logging
from uuid import uuid4

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Role, Part, TextPart, AgentCard, AgentSkill
from a2a.utils import new_task

from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.app_sessions import AppContainer

from config.settings import settings
from agent.graph import process_message

logger = logging.getLogger("personal_assistant.server")

factory = AgntcyFactory("orchestrator.personal_assistant", enable_tracing=False)

# Agent Card for A2A
PersonalAssistantCard = AgentCard(
    name="Personal Assistant Agent",
    description="Personal assistant with weather, web search, and productivity tools",
    version="1.0.0",
    url=f"http://localhost:{settings.port}",
    skills=[
        AgentSkill(
            id="weather",
            name="Weather Information",
            description="Get current weather and forecasts for any location",
            tags=["weather", "forecast", "temperature"]
        ),
        AgentSkill(
            id="search",
            name="Web Search",
            description="Search the web for current information",
            tags=["search", "web", "research"]
        ),
        AgentSkill(
            id="assistant",
            name="Personal Assistant",
            description="General personal assistance and Q&A",
            tags=["assistant", "qa", "help"]
        )
    ]
)


class PersonalAssistantExecutor(AgentExecutor):
    """
    Personal Assistant executor using LangGraph agent.
    """
    
    def __init__(self):
        self.agent_card = PersonalAssistantCard.model_dump(mode="json", exclude_none=True)
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent task."""
        if not context or not context.message or not context.message.parts:
            logger.error("Invalid request context")
            return
        
        prompt = context.get_user_input()
        logger.info(f"Personal Assistant processing: {prompt[:100]}...")
        
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        
        try:
            # Process through LangGraph agent
            response = await process_message(prompt)
            
            message = Message(
                messageId=str(uuid4()),
                role=Role.agent,
                metadata={"name": "Personal Assistant"},
                parts=[Part(root=TextPart(text=response))],
            )
            
            await event_queue.enqueue_event(message)
            
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            error_message = Message(
                messageId=str(uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(text=f"Error: {str(e)}"))],
            )
            await event_queue.enqueue_event(error_message)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation."""
        logger.info("Request cancelled")


async def run_server():
    """Run the Personal Assistant agent using SLIM transport."""
    logger.info("Initializing Personal Assistant agent...")
    
    task_store = InMemoryTaskStore()
    executor = PersonalAssistantExecutor()
    
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )
    
    server = A2AStarletteApplication(
        agent_card=PersonalAssistantCard,
        http_handler=request_handler
    )
    
    slim_endpoint = settings.slim_endpoint
    personal_topic = settings.slim_topic
    
    logger.info(f"Creating SLIM transport: {slim_endpoint}, topic: {personal_topic}")
    
    transport = factory.create_transport(
        "SLIM",
        endpoint=slim_endpoint,
        name=f"default/default/{personal_topic}"
    )
    
    app_session = factory.create_app_session(max_sessions=1)
    app_session.add_app_container("group_session", AppContainer(
        server,
        transport=transport
    ))
    
    logger.info(f"Starting Personal Assistant on SLIM topic: {personal_topic}")
    await app_session.start_session("group_session", keep_alive=True)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_server())
