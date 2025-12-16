"""
Custom Exceptions for Carrier Service.

Provides specific error types for different failure scenarios.
"""


class CarrierServiceError(Exception):
    """Base exception for all carrier service errors."""

    def __init__(self, message: str, carrier: str | None = None):
        self.message = message
        self.carrier = carrier
        super().__init__(self.message)


class ServiceabilityError(CarrierServiceError):
    """Raised when serviceability check fails."""

    pass


class RateFetchError(CarrierServiceError):
    """Raised when rate fetching fails."""

    pass


class BookingError(CarrierServiceError):
    """Raised when shipment booking fails."""

    pass


class CarrierNotFoundError(CarrierServiceError):
    """Raised when requested carrier is not registered."""

    def __init__(self, carrier_type: str):
        super().__init__(
            message=f"Carrier '{carrier_type}' is not registered",
            carrier=carrier_type,
        )


class ValidationError(CarrierServiceError):
    """Raised when request validation fails."""

    pass
