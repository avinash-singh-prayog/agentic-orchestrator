"""Agent router."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...app.container import Container

logger = logging.getLogger("serviceability_agent.agent")

router = APIRouter(prefix="/agent", tags=["Agent"])


class PromptRequest(BaseModel):
    """Request model for agent invocation."""

    prompt: str


class AgentResponse(BaseModel):
    """Response model for agent invocation."""

    response: str
    label: dict | None = None
    error: str | None = None


@router.post("/run", response_model=AgentResponse)
async def run_agent(request: PromptRequest) -> AgentResponse:
    """
    Run the serviceability agent with a natural language prompt.

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
