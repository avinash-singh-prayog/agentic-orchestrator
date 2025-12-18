"""
Supervisor Agent Graph.
"""

from typing import Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from .state import SupervisorAgentState
from .nodes import SupervisorNodes

def should_continue(state: SupervisorAgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

def build_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    Build the supervisor agent graph.
    
    Args:
        checkpointer: Optional checkpointer for conversation persistence.
                     When provided, enables multi-turn context memory.
    """
    nodes = SupervisorNodes()
    workflow = StateGraph(SupervisorAgentState)

    workflow.add_node("supervisor", nodes.supervisor_node)
    workflow.add_node("tools", nodes.tool_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {"tools": "tools", END: END}
    )

    workflow.add_edge("tools", "supervisor")

    return workflow.compile(checkpointer=checkpointer)

