"""Health check router."""

from fastapi import APIRouter
from pydantic import BaseModel

from orchestrator.carrier_service.app.container import Container

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    carriers: list[str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    factory = Container.get_factory()
    carriers = [c.value for c in factory.get_available_carriers()]
    return HealthResponse(
        status="healthy",
        carriers=carriers,
    )
