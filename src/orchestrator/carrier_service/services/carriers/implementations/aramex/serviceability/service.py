"""
Aramex Serviceability Service.

Business logic for checking address serviceability via Aramex API.
"""

import logging
import time

from orchestrator.carrier_service.domain.models import (
    CarrierCode,
    CarrierService,
    ServiceabilityMetadataResult,
    ServiceabilityResult,
    ServiceDeliveryModes,
    ServiceProductTypes,
)
from orchestrator.carrier_service.services.carriers.implementations.aramex.client import (
    AramexClient,
    AramexClientError,
)
from orchestrator.carrier_service.services.carriers.implementations.aramex.config import AramexConfig
from orchestrator.carrier_service.services.carriers.implementations.aramex.serviceability.models import (
    AramexAddress,
    AramexClientInfo,
    AramexServiceabilityRequest,
    AramexServiceDetails,
    AramexTransaction,
)

logger = logging.getLogger("carrier.aramex.serviceability")

# Aramex supported services
ARAMEX_SERVICES = [
    CarrierService(
        service_code="PDX",
        service_name="Priority Document Express",
        tat_days=2,
        is_cod=False,
        pickup=True,
        delivery=True,
        insurance=True,
        product_types=ServiceProductTypes(commercial=True, document=True, non_document=True),
        delivery_modes=ServiceDeliveryModes(express=True, standard=False),
    ),
    CarrierService(
        service_code="PPX",
        service_name="Priority Parcel Express",
        tat_days=2,
        is_cod=False,
        pickup=True,
        delivery=True,
        insurance=True,
        product_types=ServiceProductTypes(commercial=True, document=True, non_document=True),
        delivery_modes=ServiceDeliveryModes(express=True, standard=False),
    ),
    CarrierService(
        service_code="PLX",
        service_name="Priority Letter Express",
        tat_days=2,
        is_cod=False,
        pickup=True,
        delivery=True,
        insurance=True,
        product_types=ServiceProductTypes(commercial=True, document=True, non_document=True),
        delivery_modes=ServiceDeliveryModes(express=True, standard=False),
    ),
]


class AramexServiceabilityService:
    """Service for checking address serviceability with Aramex."""

    def __init__(self, config: AramexConfig, client: AramexClient):
        self.config = config
        self.client = client

    def _build_request(
        self, postal_code: str, country_code: str, city: str = ""
    ) -> AramexServiceabilityRequest:
        """Build Aramex API request from standardized input."""
        return AramexServiceabilityRequest(
            ClientInfo=AramexClientInfo(
                UserName=self.config.username,
                Password=self.config.password,
                Version="v1.0",
                AccountNumber=self.config.account_number,
                AccountPin=self.config.account_pin,
                AccountEntity=self.config.account_entity,
                AccountCountryCode=self.config.account_country_code,
                Source=self.config.source,
            ),
            Address=AramexAddress(
                PostCode=postal_code,
                CountryCode=country_code,
                City=city,
            ),
            ServiceDetails=AramexServiceDetails(),
            Transaction=AramexTransaction(),
        )

    async def check_serviceability(
        self, origin: str, destination: str, dest_country: str = "IN", origin_country: str = "IN"
    ) -> ServiceabilityResult:
        """
        Check if Aramex can service the destination address.

        Args:
            origin: Origin postal code
            destination: Destination postal code
            dest_country: Destination country code (2-letter ISO)
            origin_country: Origin country code (2-letter ISO)

        Returns:
            ServiceabilityResult with services if serviceable
        """
        start_time = time.time()
        flow = "domestic" if origin_country == dest_country else "international"

        try:
            request = self._build_request(
                postal_code=destination,
                country_code=dest_country,
            )

            result = await self.client.check_serviceability(request.model_dump())
            response_time_ms = int((time.time() - start_time) * 1000)

            is_serviceable = result.get("is_serviced", False) and not result.get("has_errors", True)
            message = None if is_serviceable else "Aramex does not service this destination"

            logger.info(f"Aramex serviceability: {origin} -> {destination} ({dest_country}) = {is_serviceable}")

            return ServiceabilityResult(
                carrier_code=CarrierCode.ARAMEX,
                carrier_name="Aramex",
                is_serviceable=is_serviceable,
                services=ARAMEX_SERVICES if is_serviceable else [],
                response_time_ms=response_time_ms,
                message=message,
                metadata=ServiceabilityMetadataResult(
                    source_country_code=origin_country,
                    destination_country_code=dest_country,
                    flow=flow,
                    is_serviceable=is_serviceable,
                    rates_available=False,
                    rates_count=0,
                ),
            )

        except AramexClientError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Aramex API error: {e}")
            return ServiceabilityResult(
                carrier_code=CarrierCode.ARAMEX,
                carrier_name="Aramex",
                is_serviceable=False,
                services=[],
                response_time_ms=response_time_ms,
                message=f"Aramex API error: {str(e)}",
                metadata=ServiceabilityMetadataResult(
                    source_country_code=origin_country,
                    destination_country_code=dest_country,
                    flow=flow,
                    is_serviceable=False,
                ),
            )
