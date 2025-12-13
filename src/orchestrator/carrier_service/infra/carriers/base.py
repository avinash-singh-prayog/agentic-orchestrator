"""
Base Carrier Adapter.

Provides common utilities and logging for all carrier implementations.
"""

import logging
from abc import ABC

from orchestrator.carrier_service.domain.interfaces import ICarrierAdapter


class BaseCarrierAdapter(ICarrierAdapter, ABC):
    """
    Base class for carrier adapters.

    Provides common functionality like logging and error handling.
    """

    def __init__(self, name: str):
        self._name = name
        self.logger = logging.getLogger(f"carrier.{name}")

    @property
    def carrier_name(self) -> str:
        return self._name
