"""
Transaction RCA Agent - FastAPI Server.

Entry point for the transaction RCA agent API.
"""

import logging
import asyncio

# Configure logging first (needed for all modes)
from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("transaction_rca_agent")


def _create_app():
    """Create and configure FastAPI app (only needed for HTTP/dual modes)."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    from app.routers import (
        health_router,
        agent_router,
        transactions_router,
        rca_router,
        tickets_router,
    )
    from database.base import init_db
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager."""
        # Startup: Initialize database
        logger.info("Initializing database...")
        try:
            init_db()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
        
        yield
        
        # Shutdown: Cleanup if needed
        logger.info("Shutting down...")
    
    app = FastAPI(
        title="Transaction RCA Agent",
        description="AI-powered root cause analysis for unprocessed transactions",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers with PineLabs prefix
    app.include_router(health_router, prefix="/rca-pinelabs")
    app.include_router(agent_router, prefix="/rca-pinelabs/v1")
    app.include_router(transactions_router, prefix="/rca-pinelabs/v1")
    app.include_router(rca_router, prefix="/rca-pinelabs/v1")
    app.include_router(tickets_router, prefix="/rca-pinelabs/v1")
    
    return app


def main() -> None:
    """Run the HTTP server only."""
    import uvicorn
    
    app = _create_app()
    logger.info(
        f"Starting Transaction RCA Agent on {settings.host}:{settings.port}"
    )
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


async def run_dual_mode() -> None:
    """Run both HTTP (uvicorn) and SLIM servers concurrently."""
    import uvicorn
    from .server_wrapper import run_server as run_slim_server

    app = _create_app()
    logger.info(f"Starting Transaction RCA Agent in DUAL mode...")
    logger.info(f"  - HTTP server on {settings.host}:{settings.port}")
    logger.info(f"  - SLIM server for inter-agent communication")

    # Create uvicorn server config
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)

    # Run both servers concurrently
    await asyncio.gather(
        server.serve(),
        run_slim_server(),
    )


if __name__ == "__main__":
    import sys
    import asyncio

    mode = sys.argv[1] if len(sys.argv) > 1 else "http"

    if mode == "slim":
        # SLIM-only mode
        from .server_wrapper import run_server
        asyncio.run(run_server())
    elif mode == "dual":
        # Dual mode: HTTP + SLIM
        asyncio.run(run_dual_mode())
    else:
        # HTTP-only mode (default)
        main()
