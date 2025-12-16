"""Serviceability router."""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ...app.container import Container

logger = logging.getLogger("carrier_agent.serviceability")

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

    client = Container.get_serviceability_client()
    # Call the external API via client
    # Note: request payload handling might be slightly different; client expects specific args
    response = await client.check_serviceability(
        origin_pincode=origin,
        dest_pincode=destination,
        origin_country=origin_country,
        dest_country=dest_country,
        weight_kg=1.0 # Default
    )

    logger.info(f"Client Response Success: {response.success}")
    if not response.success:
        logger.error(f"Client Response Message: {response.message}")

    # Transform 'response' (ServiceabilityResponse) to 'ServiceCheckResponse' (Legacy API model)
    # The Legacy 'ServiceCheckResponse' expects 'carriers' list with 'serviceable_count'.
    
    carriers_data = []
    serviceable_count = 0
    
    if response.success:
        for p in response.partners:
            # Map Partner to expected dict format in ServiceCheckResponse
            # Note: Partner model has 'services' which has 'rate' now.
            # Legacy expected 'services' list.
            
            p_dict = p.model_dump()
            if p.is_serviceable:
                serviceable_count += 1
            
            # Legacy model expects 'carrier_code' not 'partner_code' maybe?
            # 'carriers' list items in ServiceCheckResponse are type 'dict'
            # Let's try to match the fields computed in the new Partner model dump
            # The Legacy ServiceCheckResponse defines 'carriers: list[dict]' so it's flexible.
            
            carriers_data.append(p_dict)

    return ServiceCheckResponse(
        source_postal_code=origin,
        destination_postal_code=destination,
        source_country_code=origin_country,
        destination_country_code=dest_country,
        flow=flow,
        carriers=carriers_data,
        serviceable_count=serviceable_count,
        total_carriers=len(carriers_data),
    )
