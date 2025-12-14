"""Mock Carrier - Composite Adapter."""

from typing import List

from orchestrator.carrier_service.domain.models import (
    CarrierCode, LabelResponse, RateQuote, ServiceabilityResult, ShipmentRequest,
)
from orchestrator.carrier_service.services.carriers.base import BaseCarrierAdapter
from orchestrator.carrier_service.services.carriers.implementations.mock.booking import MockBookingService
from orchestrator.carrier_service.services.carriers.implementations.mock.rates import MockRateFetcher
from orchestrator.carrier_service.services.carriers.implementations.mock.serviceability import MockServiceabilityChecker


class MockCarrierAdapter(BaseCarrierAdapter):
    """Mock carrier adapter for testing and development."""

    def __init__(self):
        super().__init__(name="MockExpress")
        self._serviceability = MockServiceabilityChecker()
        self._rates = MockRateFetcher()
        self._booking = MockBookingService()

    @property
    def carrier_type(self) -> str:
        return CarrierCode.MOCK

    async def check_serviceability(
        self,
        origin: str,
        dest: str,
        origin_country: str = "IN",
        dest_country: str = "IN",
    ) -> ServiceabilityResult:
        return await self._serviceability.check_serviceability(
            origin, dest, origin_country, dest_country
        )

    async def get_rates(self, request: ShipmentRequest) -> List[RateQuote]:
        return await self._rates.get_rates(request)

    async def create_shipment(self, request: ShipmentRequest, service_code: str) -> LabelResponse:
        return await self._booking.create_shipment(request, service_code)
