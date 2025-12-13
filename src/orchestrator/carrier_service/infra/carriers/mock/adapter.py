"""
Mock Carrier - Composite Adapter.

Combines serviceability, rates, and booking into a single adapter.
"""

from typing import List

from orchestrator.carrier_service.domain.models import (
    CarrierType,
    LabelResponse,
    RateQuote,
    ServiceabilityResult,
    ShipmentRequest,
)
from orchestrator.carrier_service.infra.carriers.base import BaseCarrierAdapter
from orchestrator.carrier_service.infra.carriers.mock.booking import MockBookingService
from orchestrator.carrier_service.infra.carriers.mock.rates import MockRateFetcher
from orchestrator.carrier_service.infra.carriers.mock.serviceability import (
    MockServiceabilityChecker,
)


class MockCarrierAdapter(BaseCarrierAdapter):
    """
    Mock carrier adapter for testing and development.

    Composes separate serviceability, rates, and booking services.
    """

    def __init__(self):
        super().__init__(name="MockExpress")
        self._serviceability = MockServiceabilityChecker()
        self._rates = MockRateFetcher()
        self._booking = MockBookingService()

    @property
    def carrier_type(self) -> str:
        return CarrierType.MOCK

    async def check_serviceability(self, origin: str, dest: str) -> ServiceabilityResult:
        """Delegate to serviceability checker."""
        return await self._serviceability.check_serviceability(origin, dest)

    async def get_rates(self, request: ShipmentRequest) -> List[RateQuote]:
        """Delegate to rate fetcher."""
        return await self._rates.get_rates(request)

    async def create_shipment(
        self, request: ShipmentRequest, service_code: str
    ) -> LabelResponse:
        """Delegate to booking service."""
        return await self._booking.create_shipment(request, service_code)
