"""Agent router."""

import logging
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.container import Container
from domain.models import TransactionContext, RCAResponse

logger = logging.getLogger("transaction_rca_agent.agent")

router = APIRouter(prefix="/agent", tags=["Agent"])


class RCAAnalysisRequest(BaseModel):
    """Request model for RCA analysis."""

    transaction_context: TransactionContext


class AgentResponse(BaseModel):
    """Response model for agent invocation."""

    response: str
    rca_response: dict | None = None
    error: str | None = None


@router.post("/run", response_model=AgentResponse)
async def run_agent(request: RCAAnalysisRequest) -> AgentResponse:
    """
    Run the transaction RCA agent with a transaction context.

    Example:
        {
            "transaction_context": {
                "transaction_id": "TXN123",
                "checkpoints": [
                    {"checkpoint_name": "ingestion", "status": "success"},
                    {"checkpoint_name": "authorization", "status": "success"},
                    {"checkpoint_name": "routing", "status": "pending"}
                ]
            }
        }

    Returns:
        Agent response with RCA analysis and human intervention prompt.
    """
    transaction_id = getattr(request.transaction_context, 'transaction_id', None) or "UNKNOWN"
    logger.info(
        f"Received RCA analysis request for transaction: {transaction_id}"
    )

    try:
        graph = Container.get_graph()

        # Convert transaction context to JSON string for the graph
        context_json = json.dumps(request.transaction_context.model_dump())

        result = await graph.invoke(context_json)

        # Extract final message
        messages = result.get("messages", [])
        last_msg = messages[-1].content if messages else "No response"

        # Extract RCA response if available
        rca_response = None
        if result.get("rca_analysis") and result.get("human_intervention"):
            from domain.models import RCAResponse

            rca_response = RCAResponse(
                rca_analysis=result["rca_analysis"],
                human_intervention=result["human_intervention"],
            ).model_dump()

        return AgentResponse(
            response=last_msg,
            rca_response=rca_response,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
