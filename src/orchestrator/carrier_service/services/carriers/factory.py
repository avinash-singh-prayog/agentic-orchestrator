"""
Carrier Factory.

Factory pattern for creating and managing carrier adapters.
"""

import logging
from typing import Dict, List

from orchestrator.carrier_service.domain.exceptions import CarrierNotFoundError
from orchestrator.carrier_service.domain.interfaces import ICarrierAdapter
from orchestrator.carrier_service.domain.models import CarrierType
from orchestrator.carrier_service.services.carriers.implementations.mock.adapter import MockCarrierAdapter

logger = logging.getLogger("carrier.factory")


class CarrierFactory:
    """Factory for creating and managing carrier adapters."""

    def __init__(self):
        self._carriers: Dict[CarrierType, ICarrierAdapter] = {}
        self._initialize_default_carriers()

    def _initialize_default_carriers(self) -> None:
        self.register(CarrierType.MOCK, MockCarrierAdapter())
        logger.info("Registered default carriers: MOCK")

    def register(self, carrier_type: CarrierType, adapter: ICarrierAdapter) -> None:
        self._carriers[carrier_type] = adapter
        logger.info(f"Registered carrier: {carrier_type}")

    def unregister(self, carrier_type: CarrierType) -> None:
        if carrier_type in self._carriers:
            del self._carriers[carrier_type]

    def get(self, carrier_type: CarrierType) -> ICarrierAdapter:
        if carrier_type not in self._carriers:
            raise CarrierNotFoundError(str(carrier_type))
        return self._carriers[carrier_type]

    def get_all(self) -> List[ICarrierAdapter]:
        return list(self._carriers.values())

    def get_available_carriers(self) -> List[CarrierType]:
        return list(self._carriers.keys())
