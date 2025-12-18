"""Health check router."""

from fastapi import APIRouter
from pydantic import BaseModel

from ...domain.models import PartnerCode

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    carriers: list[str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    carriers = [c.value for c in PartnerCode]
    return HealthResponse(
        status="healthy",
        carriers=carriers,
    )
