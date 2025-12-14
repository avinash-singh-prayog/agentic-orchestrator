"""
Aramex Carrier Provider.

Main entry point for Aramex carrier integration.
Implements ICarrierAdapter interface.
"""

import logging
from typing import List

from orchestrator.carrier_service.domain.models import (
    CarrierCode,
    LabelResponse,
    RateQuote,
    ServiceabilityResult,
    ShipmentRequest,
)
from orchestrator.carrier_service.services.carriers.base import BaseCarrierAdapter
from orchestrator.carrier_service.services.carriers.implementations.aramex.client import AramexClient
from orchestrator.carrier_service.services.carriers.implementations.aramex.config import AramexConfig
from orchestrator.carrier_service.services.carriers.implementations.aramex.serviceability import (
    AramexServiceabilityService,
)

logger = logging.getLogger("carrier.aramex")


class AramexProvider(BaseCarrierAdapter):
    """
    Aramex carrier provider.

    Implements serviceability checking via Aramex API.
    Rate and booking features are placeholders for future implementation.
    """

    def __init__(self, config: AramexConfig | None = None):
        super().__init__(name="Aramex")
        self.config = config or AramexConfig.from_settings()
        self._client = AramexClient(self.config)
        self._serviceability = AramexServiceabilityService(self.config, self._client)
        logger.info(f"Aramex provider initialized (sandbox={self.config.sandbox_mode})")

    @property
    def carrier_code(self) -> CarrierCode:
        """Return the carrier code."""
        return CarrierCode.ARAMEX

    @property
    def carrier_type(self) -> str:
        """Return carrier type for interface compatibility."""
        return CarrierCode.ARAMEX

    async def check_serviceability(
        self,
        origin: str,
        dest: str,
        origin_country: str = "IN",
        dest_country: str = "IN",
    ) -> ServiceabilityResult:
        """
        Check if Aramex can service the route.

        Args:
            origin: Origin postal code
            dest: Destination postal code
            origin_country: Origin country code (2-letter ISO)
            dest_country: Destination country code (2-letter ISO)

        Returns:
            ServiceabilityResult with is_serviceable status
        """
        return await self._serviceability.check_serviceability(
            origin, dest, dest_country, origin_country
        )

    async def get_rates(self, request: ShipmentRequest) -> List[RateQuote]:
        """
        Get shipping rates from Aramex.

        Note: Not yet implemented - placeholder for future Aramex Rate API integration.
        """
        logger.warning("Aramex rates API not yet implemented")
        return []

    async def create_shipment(self, request: ShipmentRequest, service_code: str) -> LabelResponse:
        """
        Create a shipment with Aramex.

        Note: Not yet implemented - placeholder for future Aramex Booking API integration.
        """
        raise NotImplementedError("Aramex booking API not yet implemented")

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._client.close()
