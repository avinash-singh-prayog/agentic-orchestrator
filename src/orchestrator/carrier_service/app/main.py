"""
Carrier Service - FastAPI Server.

Entry point for the carrier service API.
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.carrier_service.app.routers import (
    health_router,
    agent_router,
    carriers_router,
    serviceability_router,
)
from orchestrator.carrier_service.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("carrier_service")


# Create FastAPI app
app = FastAPI(
    title="Carrier Service",
    description="AI-powered carrier selection and shipment booking service",
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
app.include_router(health_router)
app.include_router(agent_router)
app.include_router(carriers_router)
app.include_router(serviceability_router)


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
    main()
