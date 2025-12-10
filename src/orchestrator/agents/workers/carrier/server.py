"""
Carrier Agent Server

A2A server entry point for the Carrier Agent.
Includes endpoints for booking, tracking, and cancellation.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orchestrator.agents.workers.carrier.agent import CarrierAgent
from orchestrator.agents.workers.carrier.card import CARRIER_AGENT_CARD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global agent instance
agent: CarrierAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent
    
    logger.info("Starting Carrier Agent...")
    agent = CarrierAgent()
    logger.info("Carrier Agent started successfully")
    
    yield
    
    logger.info("Shutting down Carrier Agent...")


# Create FastAPI app
app = FastAPI(
    title="Carrier Agent",
    description="Carrier booking and tracking agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ===========================
# Request/Response Models
# ===========================

class BookingRequest(BaseModel):
    """Request model for shipment booking."""
    
    quote_id: str = Field(..., description="Selected quote ID")
    order_id: str = Field(..., description="Order identifier")
    customer_id: str = Field(default="guest", description="Customer identifier")


class BookingResponse(BaseModel):
    """Response model for shipment booking."""
    
    status: str
    booking_id: str | None = None
    tracking_number: str | None = None
    carrier: str | None = None
    message: str


class TrackingResponse(BaseModel):
    """Response model for tracking lookup."""
    
    tracking_number: str
    carrier: str | None = None
    status: str
    events: list[dict[str, Any]] = []
    estimated_delivery: str | None = None


class CancellationRequest(BaseModel):
    """Request model for booking cancellation."""
    
    booking_id: str = Field(..., description="Booking ID to cancel")


class CancellationResponse(BaseModel):
    """Response model for booking cancellation."""
    
    status: str
    booking_id: str
    refund_eligible: bool = False
    message: str


# ===========================
# API Endpoints
# ===========================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "carrier-agent"}


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Get the OASF Agent Card."""
    return CARRIER_AGENT_CARD


@app.post("/book", response_model=BookingResponse)
async def book_shipment(request: BookingRequest):
    """Book a shipment with a carrier."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await agent.book_shipment(request.model_dump())
        return BookingResponse(**result)
    except Exception as e:
        logger.error(f"Error booking shipment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/track/{tracking_number}", response_model=TrackingResponse)
async def get_tracking(tracking_number: str):
    """Get tracking information for a shipment."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await agent.get_tracking(tracking_number)
        return TrackingResponse(**result)
    except Exception as e:
        logger.error(f"Error getting tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cancel", response_model=CancellationResponse)
async def cancel_booking(request: CancellationRequest):
    """Cancel an existing booking."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await agent.cancel_booking(request.booking_id)
        return CancellationResponse(**result)
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    import os
    import uvicorn
    
    port = int(os.environ.get("AGENT_PORT", 9003))
    
    uvicorn.run(
        "orchestrator.agents.workers.carrier.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
