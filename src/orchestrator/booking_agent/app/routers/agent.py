"""
Agent router for booking agent API.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from ..container import Container

router = APIRouter(tags=["Agent"])


class AgentRequest(BaseModel):
    """Request model for agent invocation."""
    prompt: str
    thread_id: Optional[str] = None


class AgentResponse(BaseModel):
    """Response model from agent invocation."""
    success: bool
    message: str
    data: Optional[dict] = None


@router.post("/agent/run")
async def run_agent(request: AgentRequest) -> AgentResponse:
    """
    Run the booking agent with a prompt.
    
    Args:
        request: Agent request containing the prompt
        
    Returns:
        AgentResponse with the result
    """
    try:
        graph = Container.get_graph()
        result = await graph.invoke(request.prompt)
        
        # Extract response message
        messages = result.get("messages", [])
        output = "No response generated"
        if messages:
            last_msg = messages[-1]
            output = getattr(last_msg, 'content', str(last_msg))
        
        return AgentResponse(
            success=True,
            message=output,
            data={
                "order_response": result.get("order_response"),
                "intent": result.get("intent").model_dump() if result.get("intent") else None,
            }
        )
        
    except Exception as e:
        return AgentResponse(
            success=False,
            message=f"Error: {str(e)}",
            data=None
        )
