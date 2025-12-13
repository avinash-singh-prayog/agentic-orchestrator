"""Mock Carrier - Serviceability Check."""

import asyncio
import logging

from orchestrator.carrier_service.domain.models import CarrierType, ServiceabilityResult

logger = logging.getLogger("carrier.mock.serviceability")


class MockServiceabilityChecker:
    """Mock implementation of serviceability check."""

    NON_SERVICEABLE_ROUTES = {("00000", "99999"), ("12345", "00000")}

    async def check_serviceability(self, origin: str, dest: str) -> ServiceabilityResult:
        await asyncio.sleep(0.1)
        is_serviceable = (origin, dest) not in self.NON_SERVICEABLE_ROUTES
        message = None if is_serviceable else "Route not serviceable by MockExpress"
        logger.info(f"Serviceability check: {origin} -> {dest} = {is_serviceable}")
        return ServiceabilityResult(
            origin=origin, destination=dest, is_serviceable=is_serviceable,
            carrier=CarrierType.MOCK, message=message,
        )
