"""Serviceability router."""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from orchestrator.carrier_service.app.container import Container

logger = logging.getLogger("carrier_service.serviceability")

router = APIRouter(tags=["Serviceability"])


class ServiceabilityCheckRequest(BaseModel):
    """Request model for serviceability check."""

    source_location: dict  # {"postal_code": "400001", "country_code": "IN"}
    destination_location: dict  # {"postal_code": "10001", "country_code": "US"}
    packages: list[dict] | None = None  # Optional package info
    carriers: list[dict] | None = None  # Optional: filter specific carriers


class ServiceCheckResponse(BaseModel):
    """Response model for serviceability check."""

    source_postal_code: str
    destination_postal_code: str
    source_country_code: str
    destination_country_code: str
    flow: str
    carriers: list[dict]
    serviceable_count: int
    total_carriers: int


@router.post("/serviceability", response_model=ServiceCheckResponse)
async def check_serviceability(request: ServiceabilityCheckRequest) -> ServiceCheckResponse:
    """
    Check serviceability across all enabled carriers.

    Example:
        POST /serviceability
        {
            "source_location": {"postal_code": "193501", "country_code": "IN"},
            "destination_location": {"postal_code": "10001", "country_code": "US"}
        }

    Returns:
        List of carrier serviceability results with services.
    """
    origin = request.source_location.get("postal_code", "")
    destination = request.destination_location.get("postal_code", "")
    origin_country = request.source_location.get("country_code", "IN")
    dest_country = request.destination_location.get("country_code", "IN")
    flow = "domestic" if origin_country == dest_country else "international"

    logger.info(f"Serviceability check: {origin} ({origin_country}) -> {destination} ({dest_country})")

    orchestrator = Container.get_orchestrator()
    results = await orchestrator.check_serviceability_all(
        origin, destination, origin_country, dest_country
    )

    # Format response to match legacy API structure
    carriers = []
    for r in results:
        carrier_data = {
            "carrier_code": r.carrier_code.value,
            "carrier_name": r.carrier_name,
            "is_serviceable": r.is_serviceable,
            "services": [s.model_dump() for s in r.services],
            "response_time_ms": r.response_time_ms,
            "message": r.message,
            "metadata": r.metadata.model_dump() if r.metadata else None,
        }
        carriers.append(carrier_data)

    return ServiceCheckResponse(
        source_postal_code=origin,
        destination_postal_code=destination,
        source_country_code=origin_country,
        destination_country_code=dest_country,
        flow=flow,
        carriers=carriers,
        serviceable_count=sum(1 for r in results if r.is_serviceable),
        total_carriers=len(results),
    )
