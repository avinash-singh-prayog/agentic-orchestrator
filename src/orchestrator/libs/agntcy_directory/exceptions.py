"""
Custom exceptions for the Directory Client library.
"""


class DirectoryError(Exception):
    """Base exception for all directory client errors."""
    pass


class ConnectionError(DirectoryError):
    """Raised when connection to Directory Service fails."""
    pass


class RecordNotFoundError(DirectoryError):
    """Raised when a record is not found by CID."""
    pass


class RegistrationError(DirectoryError):
    """Raised when agent registration (push) fails."""
    pass


class SearchError(DirectoryError):
    """Raised when search operation fails."""
    pass


class ValidationError(DirectoryError):
    """Raised when record validation fails."""
    pass
