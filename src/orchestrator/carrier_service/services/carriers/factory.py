"""
Carrier Factory.

Factory pattern for creating and managing carrier adapters.
"""

import logging
from typing import Dict, List

from orchestrator.carrier_service.config.settings import settings
from orchestrator.carrier_service.domain.exceptions import CarrierNotFoundError
from orchestrator.carrier_service.domain.interfaces import ICarrierAdapter
from orchestrator.carrier_service.domain.models import CarrierCode

logger = logging.getLogger("carrier.factory")


class CarrierFactory:
    """Factory for creating and managing carrier adapters."""

    def __init__(self):
        self._carriers: Dict[CarrierCode, ICarrierAdapter] = {}
        self._initialize_carriers()

    def _initialize_carriers(self) -> None:
        """Initialize carriers based on configuration."""
        registered = []

        # Aramex carrier
        if settings.aramex_enabled:
            from orchestrator.carrier_service.services.carriers.implementations.aramex import (
                AramexProvider,
            )
            self.register(CarrierCode.ARAMEX, AramexProvider())
            registered.append("ARAMEX")

        # Add more carriers here as they are integrated
        # if settings.dhl_enabled:
        #     from ...dhl import DHLProvider
        #     self.register(CarrierCode.DHL, DHLProvider())
        #     registered.append("DHL")

        if registered:
            logger.info(f"Registered carriers: {', '.join(registered)}")
        else:
            logger.warning("No carriers registered! Enable at least one carrier in settings.")

    def register(self, carrier_code: CarrierCode, adapter: ICarrierAdapter) -> None:
        """Register a carrier adapter."""
        self._carriers[carrier_code] = adapter
        logger.info(f"Registered carrier: {carrier_code}")

    def unregister(self, carrier_code: CarrierCode) -> None:
        """Unregister a carrier adapter."""
        if carrier_code in self._carriers:
            del self._carriers[carrier_code]

    def get(self, carrier_code: CarrierCode) -> ICarrierAdapter:
        """Get a carrier adapter by code."""
        if carrier_code not in self._carriers:
            raise CarrierNotFoundError(str(carrier_code))
        return self._carriers[carrier_code]

    def get_all(self) -> List[ICarrierAdapter]:
        """Get all registered carrier adapters."""
        return list(self._carriers.values())

    def get_available_carriers(self) -> List[CarrierCode]:
        """Get list of available carrier codes."""
        return list(self._carriers.keys())
