"""
Supervisor Agent API.

Entry point for the supervisor agent with factory initialization.
"""

import json
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
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

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """Run the supervisor agent workflow (sync mode)."""
    session_start()  # Start tracing session
    initial_state = {"messages": [HumanMessage(content=request.prompt)]}
    result = await graph.ainvoke(initial_state)
    last_msg = result["messages"][-1].content
    return {"response": last_msg}


async def stream_events(prompt: str) -> AsyncGenerator[str, None]:
    """Stream events from the LangGraph workflow."""
    initial_state = {"messages": [HumanMessage(content=prompt)]}
    
    # Send initial event
    yield json.dumps({
        "content": {
            "sender": "Supervisor",
            "message": "Processing your request...",
            "node": "supervisor"
        }
    }) + "\n"
    
    last_content = ""
    current_node = "supervisor"
    
    async for event in graph.astream_events(initial_state, version="v2"):
        event_type = event.get("event", "")
        
        # Track node transitions
        if event_type == "on_chain_start":
            node_name = event.get("name", "")
            if node_name in ["supervisor", "tools"]:
                current_node = node_name
                sender = "Supervisor" if node_name == "supervisor" else "Carrier Agent"
                yield json.dumps({
                    "content": {
                        "sender": sender,
                        "message": f"Executing {node_name} node...",
                        "node": node_name
                    }
                }) + "\n"
        
        # Capture tool calls
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "unknown")
            yield json.dumps({
                "content": {
                    "sender": "Supervisor",
                    "message": f"Calling {tool_name}...",
                    "node": "tools"
                }
            }) + "\n"
        
        # Capture tool results
        elif event_type == "on_tool_end":
            tool_output = event.get("data", {}).get("output", "")
            if tool_output:
                yield json.dumps({
                    "content": {
                        "sender": "Carrier Agent",
                        "message": str(tool_output)[:200] + "...",
                        "node": "carrier"
                    }
                }) + "\n"
        
        # Capture final AI messages
        elif event_type == "on_chain_end":
            output = event.get("data", {}).get("output", {})
            if isinstance(output, dict) and "messages" in output:
                messages = output["messages"]
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, "content") and last_msg.content:
                        last_content = last_msg.content
    
    # Final response
    if last_content:
        yield json.dumps({
            "content": {
                "sender": "Supervisor",
                "message": last_content,
                "node": "supervisor",
                "final": True
            }
        }) + "\n"


@app.post("/supervisor/v1/agent/stream")
async def stream_agent(request: ChatRequest):
    """Stream the supervisor agent workflow with SSE."""
    session_start()
    return StreamingResponse(
        stream_events(request.prompt),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

