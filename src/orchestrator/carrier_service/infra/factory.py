"""
Carrier Factory.

Factory pattern implementation for creating and managing carrier adapters.
Provides registry for available carriers.
"""

import logging
from typing import Dict, List

from orchestrator.carrier_service.domain.exceptions import CarrierNotFoundError
from orchestrator.carrier_service.domain.interfaces import ICarrierAdapter
from orchestrator.carrier_service.domain.models import CarrierType
from orchestrator.carrier_service.infra.carriers.mock.adapter import MockCarrierAdapter

logger = logging.getLogger("carrier.factory")


class CarrierFactory:
    """
    Factory for creating and managing carrier adapters.

    Implements the Factory Pattern with a registry of available carriers.
    """

    def __init__(self):
        self._carriers: Dict[CarrierType, ICarrierAdapter] = {}
        self._initialize_default_carriers()

    def _initialize_default_carriers(self) -> None:
        """Register default carriers."""
        # Always register mock adapter for testing
        self.register(CarrierType.MOCK, MockCarrierAdapter())
        logger.info("Registered default carriers: MOCK")

        # Future: Register real carriers based on config
        # if settings.dhl_enabled:
        #     self.register(CarrierType.DHL, DHLAdapter(api_key=settings.dhl_api_key))

    def register(self, carrier_type: CarrierType, adapter: ICarrierAdapter) -> None:
        """
        Register a carrier adapter.

        Args:
            carrier_type: Type of carrier
            adapter: Adapter instance implementing ICarrierAdapter
        """
        self._carriers[carrier_type] = adapter
        logger.info(f"Registered carrier: {carrier_type}")

    def unregister(self, carrier_type: CarrierType) -> None:
        """
        Unregister a carrier adapter.

        Args:
            carrier_type: Type of carrier to remove
        """
        if carrier_type in self._carriers:
            del self._carriers[carrier_type]
            logger.info(f"Unregistered carrier: {carrier_type}")

    def get(self, carrier_type: CarrierType) -> ICarrierAdapter:
        """
        Get a specific carrier adapter.

        Args:
            carrier_type: Type of carrier to retrieve

        Returns:
            The carrier adapter

        Raises:
            CarrierNotFoundError: If carrier is not registered
        """
        if carrier_type not in self._carriers:
            raise CarrierNotFoundError(str(carrier_type))
        return self._carriers[carrier_type]

    def get_all(self) -> List[ICarrierAdapter]:
        """
        Get all registered carrier adapters.

        Returns:
            List of all registered adapters
        """
        return list(self._carriers.values())

    def get_available_carriers(self) -> List[CarrierType]:
        """
        Get list of available carrier types.

        Returns:
            List of registered carrier types
        """
        return list(self._carriers.keys())
