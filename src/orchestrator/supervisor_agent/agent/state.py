"""
Supervisor Agent State.
"""

from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
import operator

class SupervisorAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next_step: str
    llm_config: Optional[Dict[str, str]]  # User LLM configuration