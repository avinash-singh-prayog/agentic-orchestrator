"""
Serviceability Service - FastAPI Server.

Entry point for the serviceability service API.
"""

import logging
import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    health_router,
    agent_router,
    serviceability_router,
)
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("serviceability_agent")


# Create FastAPI app
app = FastAPI(
    title="Serviceability Agent",
    description="AI-powered serviceability checks and shipment booking agent",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Include routers
app.include_router(health_router, prefix="/serviceability-agent")
app.include_router(agent_router, prefix="/serviceability-agent/v1")
app.include_router(serviceability_router, prefix="/serviceability-agent/v1")


# ============================================================================
# OASF Discovery Endpoint
# ============================================================================

@app.get("/.well-known/agent.json")
async def get_agent_record():
    """OASF Agent Discovery endpoint - returns agent record for interoperability."""
    from pathlib import Path
    import json
    from fastapi import HTTPException
    
    record_path = Path(__file__).parent.parent / "agent_record.json"
    try:
        with open(record_path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent record not found")


def main() -> None:
    """Run the HTTP server only."""
    logger.info(f"Starting Serviceability Service on {settings.host}:{settings.port}")
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


async def run_dual_mode() -> None:
    """Run both HTTP (uvicorn) and SLIM servers concurrently."""
    import uvicorn
    from .server_wrapper import run_server as run_slim_server
    
    logger.info(f"Starting Serviceability Agent in DUAL mode...")
    logger.info(f"  - HTTP server on {settings.host}:{settings.port}")
    logger.info(f"  - SLIM server for inter-agent communication")
    
    # Register with Directory Service (auto-registration at startup)
    try:
        from agent.directory import DirectoryClient
        DirectoryClient().register_agent()
    except Exception as e:
        logger.error(f"Failed to register with Directory Service: {e}")

    # Create uvicorn server config
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    
    # Run both servers concurrently
    await asyncio.gather(
        server.serve(),
        run_slim_server(),
    )


if __name__ == "__main__":
    import sys
    import asyncio
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"
    
    if mode == "slim":
        # SLIM-only mode
        from .server_wrapper import run_server
        asyncio.run(run_server())
    elif mode == "dual":
        # Dual mode: HTTP + SLIM
        asyncio.run(run_dual_mode())
    else:
        # HTTP-only mode (default)
        main()
