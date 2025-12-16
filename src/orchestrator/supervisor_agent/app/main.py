"""
Supervisor Agent API.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import build_graph

app = FastAPI(title="Supervisor Agent")
graph = build_graph()

class ChatRequest(BaseModel):
    prompt: str

from langchain_core.messages import HumanMessage

@app.post("/supervisor/v1/agent/run")
async def run_agent(request: ChatRequest):
    initial_state = {"messages": [HumanMessage(content=request.prompt)]}
    result = await graph.ainvoke(initial_state)
    last_msg = result["messages"][-1].content
    return {"response": last_msg}

@app.get("/health")
async def health():
    return {"status": "ok"}
