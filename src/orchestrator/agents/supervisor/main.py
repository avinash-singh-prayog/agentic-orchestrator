"""
Orchestrator Supervisor FastAPI Server

Main entry point for the Supervisor Agent.
Provides REST API endpoints for:
- Synchronous prompt processing
- Streaming responses
- AgentCard discovery
- Health checks
- Admin approval endpoints (for HITL testing)
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from orchestrator.agents.supervisor.graph import OrchestratorGraph
from orchestrator.agents.supervisor.card import get_agent_card
from orchestrator.agents.supervisor.hitl import get_hitl_manager
from orchestrator.common.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global graph instance
orchestrator: OrchestratorGraph | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestrator
    
    logger.info("Starting Orchestrator Supervisor...")
    
    # Initialize the orchestrator graph
    orchestrator = OrchestratorGraph()
    
    logger.info("Orchestrator Supervisor started successfully")
    
    yield
    
    logger.info("Shutting down Orchestrator Supervisor...")


# Create FastAPI app
app = FastAPI(
    title="Orchestrator Supervisor",
    description="Multi-agent logistics orchestration supervisor",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================
# Request/Response Models
# ===========================

class PromptRequest(BaseModel):
    """Request model for prompt processing."""
    
    prompt: str = Field(..., description="User prompt to process")
    order_id: str | None = Field(default=None, description="Optional order ID")
    customer_id: str | None = Field(default=None, description="Customer identifier")
    origin: str | None = Field(default=None, description="Shipping origin")
    destination: str | None = Field(default=None, description="Shipping destination")
    shipments: list[dict[str, Any]] | None = Field(default=None, description="Shipment data")


class PromptResponse(BaseModel):
    """Response model for prompt processing."""
    
    response: str = Field(..., description="Agent response")
    order_id: str | None = Field(default=None, description="Order ID if applicable")
    status: str = Field(default="success", description="Processing status")


class ApprovalRequest(BaseModel):
    """Request model for approving HITL interrupts."""
    
    interrupt_id: str = Field(..., description="HITL interrupt ID to approve")
    approver_id: str = Field(default="admin", description="Approver identifier")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    agent: str = Field(default="orchestrator-supervisor")


# ===========================
# API Endpoints
# ===========================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/.well-known/agent.json", tags=["Discovery"])
async def get_agent_card_endpoint():
    """
    Get the OASF Agent Card.
    
    This endpoint enables agent discovery following the
    Open Agent Schema Framework specification.
    """
    return get_agent_card()


@app.post("/agent/prompt", response_model=PromptResponse, tags=["Agent"])
async def process_prompt(request: PromptRequest):
    """
    Process a prompt synchronously.
    
    This endpoint processes the user's prompt through the
    orchestration workflow and returns the final response.
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    context = {
        "order_id": request.order_id or str(uuid4())[:8],
        "customer_id": request.customer_id or "guest",
        "origin": request.origin or "",
        "destination": request.destination or "",
        "shipments": request.shipments or [],
    }
    
    try:
        response = await orchestrator.serve(request.prompt, context)
        
        return PromptResponse(
            response=response,
            order_id=context["order_id"],
            status="success",
        )
    except Exception as e:
        logger.error(f"Error processing prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/prompt/stream", tags=["Agent"])
async def process_prompt_stream(request: PromptRequest):
    """
    Process a prompt with streaming response.
    
    Returns an NDJSON stream of response chunks as they
    are generated by the orchestration workflow.
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    context = {
        "order_id": request.order_id or str(uuid4())[:8],
        "customer_id": request.customer_id or "guest",
        "origin": request.origin or "",
        "destination": request.destination or "",
        "shipments": request.shipments or [],
    }
    
    async def generate():
        try:
            async for chunk in orchestrator.streaming_serve(request.prompt, context):
                yield json.dumps({"content": chunk}) + "\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"error": str(e)}) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"X-Order-ID": context["order_id"]},
    )


# ===========================
# Admin Endpoints (HITL)
# ===========================

@app.get("/admin/pending-approvals", tags=["Admin"])
async def list_pending_approvals():
    """List all pending HITL approval requests."""
    hitl_manager = get_hitl_manager()
    
    pending = [
        {
            "interrupt_id": interrupt.interrupt_id,
            "order_id": interrupt.order_id,
            "reason": interrupt.reason,
            "action": interrupt.required_action,
            "context": interrupt.context,
            "created_at": interrupt.created_at.isoformat(),
        }
        for interrupt in hitl_manager._pending_interrupts.values()
        if interrupt.approval_status == "pending"
    ]
    
    return {"pending_approvals": pending, "count": len(pending)}


@app.post("/admin/approve", tags=["Admin"])
async def approve_interrupt(request: ApprovalRequest):
    """
    Approve a pending HITL interrupt.
    
    This endpoint is used for testing and admin approval
    of high-value orders.
    """
    hitl_manager = get_hitl_manager()
    
    try:
        interrupt = await hitl_manager.approve(
            interrupt_id=request.interrupt_id,
            approved_by=request.approver_id,
        )
        
        return {
            "status": "approved",
            "interrupt_id": interrupt.interrupt_id,
            "order_id": interrupt.order_id,
            "approved_by": interrupt.approved_by,
            "approved_at": interrupt.approved_at.isoformat() if interrupt.approved_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/admin/reject", tags=["Admin"])
async def reject_interrupt(request: ApprovalRequest, reason: str = ""):
    """Reject a pending HITL interrupt."""
    hitl_manager = get_hitl_manager()
    
    try:
        interrupt = await hitl_manager.reject(
            interrupt_id=request.interrupt_id,
            rejected_by=request.approver_id,
            reason=reason,
        )
        
        return {
            "status": "rejected",
            "interrupt_id": interrupt.interrupt_id,
            "order_id": interrupt.order_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "orchestrator.agents.supervisor.main:app",
        host="0.0.0.0",
        port=settings.supervisor_port,
        reload=True,
    )
