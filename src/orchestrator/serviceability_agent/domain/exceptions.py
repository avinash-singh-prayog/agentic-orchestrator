"""
Custom Exceptions for Serviceability Agent.

Provides specific error types for different failure scenarios.
"""


class ServiceabilityAgentError(Exception):
    """Base exception for all serviceability agent errors."""

    def __init__(self, message: str, carrier: str | None = None):
        self.message = message
        self.carrier = carrier
        super().__init__(self.message)


class ServiceabilityError(ServiceabilityAgentError):
    """Raised when serviceability check fails."""

    pass


class RateFetchError(ServiceabilityAgentError):
    """Raised when rate fetching fails."""

    pass


class BookingError(ServiceabilityAgentError):
    """Raised when shipment booking fails."""

    pass


class CarrierNotFoundError(ServiceabilityAgentError):
    """Raised when requested carrier is not registered."""

    def __init__(self, carrier_type: str):
        super().__init__(
            message=f"Carrier '{carrier_type}' is not registered",
            carrier=carrier_type,
        )


class ValidationError(ServiceabilityAgentError):
    """Raised when request validation fails."""

    pass
