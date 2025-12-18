"""
Serviceability Service Client.

Interacts with the internal serviceability API.
"""

import os
import httpx
import logging
from typing import Optional, Dict, Any, List

from ...domain.models import ServiceabilityResponse, ServiceabilityRequest, Location, Package, Weight, Dimensions

logger = logging.getLogger("serviceability_agent.serviceability.client")

# Configure via environment variable - required, no default
SERVICEABILITY_API_URL = os.getenv("SERVICEABILITY_API_URL")
if not SERVICEABILITY_API_URL:
    raise ValueError("SERVICEABILITY_API_URL environment variable is required but not set")

class ServiceabilityClient:
    """Client for the internal serviceability service."""

    def __init__(self, base_url: str = SERVICEABILITY_API_URL):
        self.base_url = base_url
        logger.info(f"ServiceabilityClient initialized with URL: {self.base_url}")
    
    async def check_serviceability(
        self,
        origin_pincode: str,
        dest_pincode: str,
        origin_country: str = "IN",
        dest_country: str = "IN",
        weight_kg: float = 1.0,
        length_cm: float = 10.0,
        width_cm: float = 10.0,
        height_cm: float = 10.0,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> ServiceabilityResponse:
        """
        Check serviceability between two locations.
        """
        payload = {
            "source_location": {
                "postal_code": origin_pincode,
                "country_code": origin_country
            },
            "destination_location": {
                "postal_code": dest_pincode,
                "country_code": dest_country
            },
            "packages": [
                {
                    "weight": {
                        "value": weight_kg,
                        "unit": "kg"
                    },
                    "dimensions": {
                        "length": length_cm,
                        "width": width_cm,
                        "height": height_cm,
                        "unit": "cm"
                    }
                }
            ]
        }

        headers = {
            "content-type": "application/json",
            "x-tenant-id": tenant_id or "507f1f77bcf86cd799439011", # Default from example
            "x-user-id": user_id or "550e8400-e29b-41d4-a716-446655440000" # Default from example
        }

        logger.info(f"Checking serviceability [API]: {origin_pincode} -> {dest_pincode}")

        async with httpx.AsyncClient() as client:
            try:
                url = self.base_url + '/serviceability/v3/check'
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return ServiceabilityResponse(**data)
            except httpx.HTTPError as e:
                logger.error(f"Serviceability API call failed: {type(e).__name__}: {e}")
                return ServiceabilityResponse(
                    success=False,
                    message=f"API Request failed: {str(e)}",
                    partners=[]
                )
            except Exception as e:
                logger.error(f"Unexpected error in serviceability client: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return ServiceabilityResponse(
                    success=False,
                    message=f"Internal error: {str(e)}",
                    partners=[]
                )
