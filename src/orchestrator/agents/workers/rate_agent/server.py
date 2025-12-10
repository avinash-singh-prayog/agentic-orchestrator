"""
Rate Agent Server

A2A server entry point for the Rate Agent.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orchestrator.agents.workers.rate_agent.agent import RateAgent
from orchestrator.agents.workers.rate_agent.card import RATE_AGENT_CARD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global agent instance
agent: RateAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent
    
    logger.info("Starting Rate Agent...")
    agent = RateAgent()
    logger.info("Rate Agent started successfully")
    
    yield
    
    logger.info("Shutting down Rate Agent...")


# Create FastAPI app
app = FastAPI(
    title="Rate Agent",
    description="Multi-carrier rate aggregation agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ===========================
# Request/Response Models
# ===========================

class RateRequest(BaseModel):
    """Request model for rate quotes."""
    
    origin: str = Field(..., description="Origin address")
    destination: str = Field(..., description="Destination address")
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms")
    dimensions: str = Field(default="", description="Dimensions in LxWxH cm")


class Quote(BaseModel):
    """Individual carrier quote."""
    
    carrier: str
    service: str
    price: float
    currency: str
    estimated_days: int
    quote_id: str


class RateResponse(BaseModel):
    """Response model for rate quotes."""
    
    origin: str
    destination: str
    weight_kg: float
    quotes: list[dict[str, Any]]
    best_price: dict[str, Any] | None
    fastest: dict[str, Any] | None
    quote_count: int


# ===========================
# API Endpoints
# ===========================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "rate-agent"}


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Get the OASF Agent Card."""
    return RATE_AGENT_CARD


@app.post("/quotes", response_model=RateResponse)
async def get_rates(request: RateRequest):
    """Get shipping rate quotes from all carriers."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await agent.ainvoke(request.model_dump())
        return RateResponse(**result)
    except Exception as e:
        logger.error(f"Error getting rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    import os
    import uvicorn
    
    port = int(os.environ.get("AGENT_PORT", 9002))
    
    uvicorn.run(
        "orchestrator.agents.workers.rate_agent.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
