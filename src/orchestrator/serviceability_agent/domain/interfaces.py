"""
Domain Interfaces for Serviceability Agent.

Abstract Base Classes defining the contract every adapter must implement.
Follows Interface Segregation Principle - separate interfaces for each responsibility.
"""

from abc import ABC, abstractmethod
from typing import List

from .models import (
    LabelResponse,
    RateQuote,
    ServiceabilityResult,
    ShipmentRequest,
)


class IServiceabilityChecker(ABC):
    """Interface for checking if a route is serviceable."""

    @abstractmethod
    async def check_serviceability(
        self,
        origin: str,
        dest: str,
        origin_country: str = "IN",
        dest_country: str = "IN",
    ) -> ServiceabilityResult:
        """
        Check if shipping is available between origin and destination.

        Args:
            origin: Origin postal/pin code
            dest: Destination postal/pin code
            origin_country: Origin country code (2-letter ISO)
            dest_country: Destination country code (2-letter ISO)

        Returns:
            ServiceabilityResult with availability status
        """
        pass



class IRateFetcher(ABC):
    """Interface for fetching shipping rates."""

    @abstractmethod
    async def get_rates(self, request: ShipmentRequest) -> List[RateQuote]:
        """
        Get available shipping rates for a shipment.

        Args:
            request: Shipment details

        Returns:
            List of available rate quotes
        """
        pass


class IBookingService(ABC):
    """Interface for creating shipments and booking labels."""

    @abstractmethod
    async def create_shipment(
        self, request: ShipmentRequest, service_code: str
    ) -> LabelResponse:
        """
        Create a shipment and generate a label.

        Args:
            request: Shipment details
            service_code: Selected service code from rate quote

        Returns:
            LabelResponse with tracking number and label URL
        """
        pass


class IServiceabilityAdapter(IServiceabilityChecker, IRateFetcher, IBookingService):
    """
    Composite interface for a complete serviceability adapter.

    Extends all three interfaces: serviceability, rates, and booking.
    All adapter implementations must implement this interface.
    """

    @property
    @abstractmethod
    def carrier_type(self) -> str:
        """Return the carrier type identifier."""
        pass

    @property
    @abstractmethod
    def carrier_name(self) -> str:
        """Return the human-readable carrier name."""
        pass
