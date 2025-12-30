"""
Personal Assistant Agent - FastAPI Application.

Entry point for HTTP server with health checks and OASF discovery.
Runs in dual mode: HTTP + SLIM.
"""
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("personal_assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    logger.info(f"Personal Assistant Agent starting on port {settings.port}")
    
    try:
        from agent.directory import DirectoryClient
        DirectoryClient().register_agent()
    except Exception as e:
        logger.warning(f"Directory registration failed: {e}")
    
    yield
    
    logger.info("Personal Assistant Agent shutting down")


app = FastAPI(
    title="Personal Assistant Agent",
    description="Personal assistant with weather, web search, and productivity tools",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/personal-assistant/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="ok", service="personal-assistant-agent")


@app.get("/.well-known/agent.json")
async def get_agent_record():
    """OASF Agent Discovery endpoint."""
    from pathlib import Path
    import json
    
    record_path = Path(__file__).parent.parent / "agent_record.json"
    try:
        with open(record_path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Agent record not found"}


@app.post("/personal-assistant/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """HTTP endpoint for chat (for testing)."""
    from agent.graph import process_message
    
    response = await process_message(request.message)
    return ChatResponse(response=response)


def main() -> None:
    """Run HTTP server only."""
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


async def run_dual_mode() -> None:
    """Run both HTTP and SLIM servers."""
    from app.server_wrapper import run_server as run_slim_server
    
    logger.info(f"Starting Personal Assistant in DUAL mode...")
    
    try:
        from agent.directory import DirectoryClient
        DirectoryClient().register_agent()
    except Exception as e:
        logger.warning(f"Directory registration failed: {e}")
    
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        run_slim_server(),
    )


if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"
    
    if mode == "slim":
        from app.server_wrapper import run_server
        asyncio.run(run_server())
    elif mode == "dual":
        asyncio.run(run_dual_mode())
    else:
        main()
