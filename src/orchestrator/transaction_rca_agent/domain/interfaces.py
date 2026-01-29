"""
Service interfaces for Transaction RCA Agent.
"""

from abc import ABC, abstractmethod
from domain.models import TransactionContext, RCAResponse


class RCAAnalysisService(ABC):
    """Interface for RCA analysis service."""

    @abstractmethod
    async def analyze_transaction(self, context: TransactionContext) -> RCAResponse:
        """Perform RCA analysis on a transaction."""
        pass
