"""
Supervisor Agent API.

Entry point for the supervisor agent with factory initialization.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agntcy_app_sdk.factory import AgntcyFactory
from agent.shared import set_factory
from agent.graph import build_graph

# Try to import observability
try:
    from ioa_observe.sdk.tracing import session_start
    HAS_OBSERVABILITY = True
except ImportError:
    def session_start():
        pass
    HAS_OBSERVABILITY = False

app = FastAPI(title="Supervisor Agent")


@app.on_event("startup")
async def startup():
    """Initialize the AgntcyFactory on startup."""
    set_factory(AgntcyFactory("orchestrator.supervisor_agent", enable_tracing=True))


# Build graph after app is created
graph = build_graph()


class ChatRequest(BaseModel):
    prompt: str


@app.post("/supervisor/v1/agent/run")
async def run_agent(request: ChatRequest):
    """Run the supervisor agent workflow."""
    session_start()  # Start tracing session
    initial_state = {"messages": [HumanMessage(content=request.prompt)]}
    result = await graph.ainvoke(initial_state)
    last_msg = result["messages"][-1].content
    return {"response": last_msg}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
