"""
Custom exceptions for Transaction RCA Agent.
"""


class TransactionRCAError(Exception):
    """Base exception for Transaction RCA Agent errors."""

    pass


class InvalidTransactionContextError(TransactionRCAError):
    """Raised when transaction context is invalid."""

    pass


class RCAAnalysisError(TransactionRCAError):
    """Raised when RCA analysis fails."""

    pass
