"""Carriers router."""

from fastapi import APIRouter

from orchestrator.carrier_service.app.container import Container

router = APIRouter(tags=["Carriers"])


@router.get("/carriers")
async def list_carriers() -> dict:
    """List all available carriers."""
    factory = Container.get_factory()
    carriers = []
    for adapter in factory.get_all():
        carriers.append({
            "code": str(adapter.carrier_type),
            "name": adapter.carrier_name,
        })
    return {"carriers": carriers}
