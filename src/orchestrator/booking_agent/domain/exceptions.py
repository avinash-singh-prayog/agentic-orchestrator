"""
Booking Agent Domain Exceptions.

Custom exceptions for order processing errors.
"""


class BookingAgentError(Exception):
    """Base exception for booking agent."""
    pass


class OrderCreationError(BookingAgentError):
    """Error during order creation."""
    pass


class OrderNotFoundError(BookingAgentError):
    """Order not found."""
    pass


class OrderCancellationError(BookingAgentError):
    """Error during order cancellation."""
    pass


class OrderValidationError(BookingAgentError):
    """Order validation failed."""
    pass


class OrderAPIError(BookingAgentError):
    """Error communicating with Order API."""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code
