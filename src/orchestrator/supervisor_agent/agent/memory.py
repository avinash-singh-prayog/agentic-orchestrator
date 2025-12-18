"""
Memory module for supervisor agent.

Provides LangGraph checkpointer for conversation persistence.
"""

import os
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# PostgreSQL connection string for multi-tenant chat history
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://orchestrator_supervisor_agent:pFaiA88gRFFwrF@prayog-orchestrator-sandbox.c7geye6morpj.ap-south-1.rds.amazonaws.com:5432/orchestrator_supervisor_prod"
)


@asynccontextmanager
async def get_checkpointer():
    """
    Get async PostgreSQL checkpointer for LangGraph.
    
    Yields:
        AsyncPostgresSaver: Configured checkpointer instance
    """
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()  # Create tables if not exist
        yield checkpointer
