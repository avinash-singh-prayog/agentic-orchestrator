"""
Carrier Service - FastAPI Server.

Entry point for the carrier service API.
"""

import logging

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator.carrier_service.app.container import Container
from orchestrator.carrier_service.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("carrier_service")


# Request/Response models
class PromptRequest(BaseModel):
    """Request model for agent invocation."""

    prompt: str


class AgentResponse(BaseModel):
    """Response model for agent invocation."""

    response: str
    label: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    carriers: list[str]


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


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    factory = Container.get_factory()
    carriers = [c.value for c in factory.get_available_carriers()]
    return HealthResponse(
        status="healthy",
        carriers=carriers,
    )


@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: PromptRequest) -> AgentResponse:
    """
    Run the carrier agent with a natural language prompt.

    Example:
        {"prompt": "I need to ship a 2.5kg box from 10001 to 90210"}

    Returns:
        Agent response with shipping details and label if booked.
    """
    logger.info(f"Received prompt: {request.prompt[:100]}...")

    try:
        graph = Container.get_graph()
        result = await graph.invoke(request.prompt)

        # Extract final message
        messages = result.get("messages", [])
        last_msg = messages[-1].content if messages else "No response"

        # Extract label if booking was successful
        label = None
        if result.get("final_label"):
            label_obj = result["final_label"]
            # Handle both dict (from tools) and Pydantic model
            if isinstance(label_obj, dict):
                label = {
                    "tracking_number": label_obj.get("tracking_number"),
                    "label_url": label_obj.get("label_url"),
                    "carrier": label_obj.get("carrier"),
                }
            else:
                label = {
                    "tracking_number": label_obj.tracking_number,
                    "label_url": label_obj.label_url,
                    "carrier": label_obj.carrier.value,
                }

        return AgentResponse(
            response=last_msg,
            label=label,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/carriers")
async def list_carriers() -> dict:
    """List all available carriers."""
    factory = Container.get_factory()
    carriers = []
    for adapter in factory.get_all():
        carriers.append({
            "type": str(adapter.carrier_type),
            "name": adapter.carrier_name,
        })
    return {"carriers": carriers}


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
