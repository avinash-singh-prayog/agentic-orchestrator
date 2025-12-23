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




# Global singleton instance
_checkpointer_instance = None

@asynccontextmanager
async def checkpointer_lifespan():
    """Application lifespan manager for the global checkpointer."""
    global _checkpointer_instance
    # Initialize checkpointer with connection pool
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        _checkpointer_instance = checkpointer
        try:
            yield
        finally:
            # Checkpointer (and pool) closes when this context exits
            _checkpointer_instance = None


@asynccontextmanager
async def get_checkpointer():
    """
    Get the shared global checkpointer instance.
    
    Yields:
        AsyncPostgresSaver: The global checkpointer
    """
    if _checkpointer_instance is None:
        # Fallback or initialization race condition protection
        # For safety in tests or scripts without lifespan, we could create one temporarily
        async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
            # await checkpointer.setup() # Assume setup done or distinct
            yield checkpointer
    else:
        yield _checkpointer_instance
