"""
Health check router.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "booking-agent"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready", "agent": "booking-agent"}
