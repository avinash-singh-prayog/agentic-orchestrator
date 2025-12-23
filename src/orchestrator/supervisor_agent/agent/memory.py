"""
Memory module for supervisor agent.

Provides LangGraph checkpointer for conversation persistence.
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Load .env file (for local development)
load_dotenv()

# PostgreSQL connection string - REQUIRED, no hardcoded fallback
_raw_db_url = os.getenv("DATABASE_URL")
if not _raw_db_url:
    raise ValueError("DATABASE_URL environment variable is required but not set")

# Strip quotes that may be accidentally included in ECS task definitions
DATABASE_URL = _raw_db_url.strip('"').strip("'")


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
