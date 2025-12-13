"""
Mock Carrier - Serviceability Check.

Simulates serviceability checking for testing purposes.
"""

import asyncio
import logging

from orchestrator.carrier_service.domain.models import CarrierType, ServiceabilityResult

logger = logging.getLogger("carrier.mock.serviceability")


class MockServiceabilityChecker:
    """Mock implementation of serviceability check."""

    # Simulated non-serviceable routes (for testing)
    NON_SERVICEABLE_ROUTES = {
        ("00000", "99999"),  # Invalid route
        ("12345", "00000"),  # Restricted destination
    }

    async def check_serviceability(self, origin: str, dest: str) -> ServiceabilityResult:
        """
        Check if route is serviceable.

        For mock: Always serviceable except for specific test routes.
        """
        # Simulate network latency
        await asyncio.sleep(0.1)

        is_serviceable = (origin, dest) not in self.NON_SERVICEABLE_ROUTES

        message = None if is_serviceable else "Route not serviceable by MockExpress"

        logger.info(
            f"Serviceability check: {origin} -> {dest} = {is_serviceable}"
        )

        return ServiceabilityResult(
            origin=origin,
            destination=dest,
            is_serviceable=is_serviceable,
            carrier=CarrierType.MOCK,
            message=message,
        )
