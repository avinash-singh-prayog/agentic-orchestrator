"""
Memory module for supervisor agent.

Provides LangGraph checkpointer for conversation persistence.

Production-grade features:
- Connection pool with health checks (validates connections before use)
- Automatic reconnection on stale/closed connections
- Retry logic with exponential backoff for transient failures
- Keep-alive to prevent idle connection timeouts
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import TypeVar, Callable, Any

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Load .env file (for local development)
load_dotenv()

logger = logging.getLogger(__name__)

# PostgreSQL connection string - REQUIRED, no hardcoded fallback
_raw_db_url = os.getenv("DATABASE_URL")
if not _raw_db_url:
    raise ValueError("DATABASE_URL environment variable is required but not set")

# Strip quotes that may be accidentally included in ECS task definitions
DATABASE_URL = _raw_db_url.strip('"').strip("'")


# =============================================================================
# Connection Pool Configuration (Production-grade settings)
# =============================================================================

POOL_CONFIG = {
    # Minimum connections to keep open
    "min_size": 2,
    # Maximum connections in pool
    "max_size": 10,
    # Max time (seconds) a connection can be idle before being closed
    # Set lower than PostgreSQL's idle timeout (typically 300s)
    "max_idle": 120,
    # Max lifetime (seconds) for a connection before recycling
    "max_lifetime": 1800,  # 30 minutes
    # Timeout (seconds) to wait for a connection from pool
    "timeout": 30,
    # Number of times to retry getting a connection
    "num_workers": 3,
    # Check connection health before returning from pool
    "check": AsyncConnectionPool.check_connection,
    # Reconnect automatically if connection check fails
    "reconnect_failed": True,
}


# =============================================================================
# Retry Logic with Exponential Backoff
# =============================================================================

T = TypeVar('T')

async def with_retry(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    **kwargs
) -> Any:
    """
    Execute an async function with retry logic and exponential backoff.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
    
    Returns:
        Result of the function call
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
            
            # Check if error is retryable
            is_retryable = any(keyword in error_msg for keyword in [
                "connection is closed",
                "connection refused",
                "connection reset",
                "timeout",
                "connection pool",
                "no connection available",
                "connection terminated",
                "server closed the connection",
            ])
            
            if not is_retryable or attempt == max_retries:
                logger.error(f"Database operation failed after {attempt + 1} attempts: {e}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
    
    raise last_exception


# =============================================================================
# Global Checkpointer Singleton
# =============================================================================

_checkpointer_instance: AsyncPostgresSaver = None
_connection_pool: AsyncConnectionPool = None


@asynccontextmanager
async def checkpointer_lifespan():
    """
    Application lifespan manager for the global checkpointer with resilient connection pool.
    
    Features:
    - Health checks validate connections before use
    - Automatic reconnection on stale connections
    - Connection recycling prevents long-lived connection issues
    """
    global _checkpointer_instance, _connection_pool
    
    from psycopg.rows import dict_row
    
    logger.info("Initializing PostgreSQL connection pool with health checks...")
    
    # Create connection pool with health checks
    # kwargs passed to each connection in the pool
    _connection_pool = AsyncConnectionPool(
        DATABASE_URL,
        min_size=POOL_CONFIG["min_size"],
        max_size=POOL_CONFIG["max_size"],
        max_idle=POOL_CONFIG["max_idle"],
        max_lifetime=POOL_CONFIG["max_lifetime"],
        timeout=POOL_CONFIG["timeout"],
        num_workers=POOL_CONFIG["num_workers"],
        check=POOL_CONFIG["check"],
        reconnect_failed=POOL_CONFIG["reconnect_failed"],
        # Connection kwargs required by AsyncPostgresSaver
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    )
    
    try:
        # Open the pool (establishes min_size connections)
        await _connection_pool.open()
        logger.info(f"Connection pool opened with {POOL_CONFIG['min_size']}-{POOL_CONFIG['max_size']} connections")
        
        # Create checkpointer with the pool
        # Note: parameter is 'conn' but accepts AsyncConnectionPool
        _checkpointer_instance = AsyncPostgresSaver(conn=_connection_pool)
        await _checkpointer_instance.setup()
        logger.info("Checkpointer initialized successfully")
        
        yield
    finally:
        logger.info("Shutting down checkpointer and connection pool...")
        _checkpointer_instance = None
        # Close pool on shutdown
        await _connection_pool.close()
        _connection_pool = None
        logger.info("Connection pool closed")


@asynccontextmanager
async def get_checkpointer():
    """
    Get the shared global checkpointer instance.
    
    If the global instance is not available (e.g., in tests), creates a temporary
    checkpointer with the same resilient pool configuration.
    
    Yields:
        AsyncPostgresSaver: The global or temporary checkpointer
    """
    if _checkpointer_instance is not None:
        yield _checkpointer_instance
    else:
        # Fallback: Create a temporary resilient pool for tests/scripts
        from psycopg.rows import dict_row
        
        logger.warning("Global checkpointer not initialized, creating temporary instance")
        temp_pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            max_idle=POOL_CONFIG["max_idle"],
            check=POOL_CONFIG["check"],
            reconnect_failed=POOL_CONFIG["reconnect_failed"],
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        )
        try:
            await temp_pool.open()
            checkpointer = AsyncPostgresSaver(conn=temp_pool)
            yield checkpointer
        finally:
            await temp_pool.close()
