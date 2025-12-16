"""
Carrier Service - FastAPI Server.

Entry point for the carrier service API.
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    health_router,
    agent_router,
    serviceability_router,
)
from ..config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("carrier_agent")


# Create FastAPI app
app = FastAPI(
    title="Carrier Agent",
    description="AI-powered carrier selection and shipment booking agent",
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
app.include_router(health_router, prefix="/carrier/v1")
app.include_router(agent_router, prefix="/carrier/v1")
app.include_router(serviceability_router, prefix="/carrier/v1")


def main() -> None:
    """Run the server."""
    logger.info(f"Starting Carrier Service on {settings.host}:{settings.port}")
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "slim":
        import asyncio
        from .server_wrapper import run_server
        asyncio.run(run_server())
    else:
        main()
