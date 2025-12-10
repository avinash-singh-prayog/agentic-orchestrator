"""
Serviceability Agent Server

A2A server entry point for the Serviceability Agent.
Provides both A2A protocol interface and REST API fallback.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orchestrator.agents.workers.serviceability.agent import ServiceabilityAgent
from orchestrator.agents.workers.serviceability.card import SERVICEABILITY_AGENT_CARD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global agent instance
agent: ServiceabilityAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent
    
    logger.info("Starting Serviceability Agent...")
    agent = ServiceabilityAgent()
    logger.info("Serviceability Agent started successfully")
    
    yield
    
    logger.info("Shutting down Serviceability Agent...")


# Create FastAPI app
app = FastAPI(
    title="Serviceability Agent",
    description="Validates shipping routes for serviceability",
    version="1.0.0",
    lifespan=lifespan,
)


# ===========================
# Request/Response Models
# ===========================

class ServiceabilityRequest(BaseModel):
    """Request model for serviceability check."""
    
    origin: str = Field(..., description="Origin address")
    destination: str = Field(..., description="Destination address")
    shipment_type: str = Field(default="standard", description="Type of shipment")


class ServiceabilityResponse(BaseModel):
    """Response model for serviceability check."""
    
    is_serviceable: bool
    origin: str
    destination: str
    available_carriers: list[str]
    reasons: list[str]
    response: str


# ===========================
# API Endpoints
# ===========================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "serviceability-agent"}


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Get the OASF Agent Card."""
    return SERVICEABILITY_AGENT_CARD


@app.post("/check", response_model=ServiceabilityResponse)
async def check_serviceability(request: ServiceabilityRequest):
    """Check if a shipping route is serviceable."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await agent.ainvoke(request.model_dump())
        return ServiceabilityResponse(**result)
    except Exception as e:
        logger.error(f"Error checking serviceability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    import os
    import uvicorn
    
    port = int(os.environ.get("AGENT_PORT", 9001))
    
    uvicorn.run(
        "orchestrator.agents.workers.serviceability.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
