"""Mock Carrier - Serviceability Check."""

import asyncio
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

logger = logging.getLogger("carrier.mock.serviceability")

# Mock carrier services
MOCK_SERVICES = [
    CarrierService(
        service_code="MOCK_STD",
        service_name="MockExpress Standard",
        tat_days=5,
        is_cod=True,
        pickup=True,
        delivery=True,
        insurance=True,
        product_types=ServiceProductTypes(commercial=True, document=True, non_document=True),
        delivery_modes=ServiceDeliveryModes(express=False, standard=True),
    ),
    CarrierService(
        service_code="MOCK_EXP",
        service_name="MockExpress Express",
        tat_days=2,
        is_cod=False,
        pickup=True,
        delivery=True,
        insurance=True,
        product_types=ServiceProductTypes(commercial=True, document=True, non_document=True),
        delivery_modes=ServiceDeliveryModes(express=True, standard=False),
    ),
]


class MockServiceabilityChecker:
    """Mock implementation of serviceability check."""

    NON_SERVICEABLE_ROUTES = {("00000", "99999"), ("12345", "00000")}

    async def check_serviceability(
        self,
        origin: str,
        dest: str,
        origin_country: str = "IN",
        dest_country: str = "IN",
    ) -> ServiceabilityResult:
        start_time = time.time()
        await asyncio.sleep(0.1)

        is_serviceable = (origin, dest) not in self.NON_SERVICEABLE_ROUTES
        message = None if is_serviceable else "Route not serviceable by MockExpress"
        flow = "domestic" if origin_country == dest_country else "international"
        response_time_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Serviceability check: {origin} -> {dest} = {is_serviceable}")

        return ServiceabilityResult(
            carrier_code=CarrierCode.MOCK,
            carrier_name="MockExpress",
            is_serviceable=is_serviceable,
            services=MOCK_SERVICES if is_serviceable else [],
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
