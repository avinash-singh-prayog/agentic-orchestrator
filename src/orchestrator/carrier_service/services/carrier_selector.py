"""
Carrier Selector.

Strategy pattern for selecting and ranking carriers/rates.
"""

import logging
from enum import Enum
from typing import List

from orchestrator.carrier_service.domain.models import RateQuote

logger = logging.getLogger("carrier.selector")


class SelectionStrategy(str, Enum):
    """Selection strategies for ranking rates."""
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BEST_VALUE = "best_value"


class CarrierSelector:
    """Strategy-based carrier and rate selection."""

    def rank_rates(self, rates: List[RateQuote], strategy: SelectionStrategy = SelectionStrategy.CHEAPEST) -> List[RateQuote]:
        """Rank rates according to the specified strategy."""
        if not rates:
            return []
        if strategy == SelectionStrategy.CHEAPEST:
            ranked = sorted(rates, key=lambda r: r.price)
        elif strategy == SelectionStrategy.FASTEST:
            ranked = sorted(rates, key=lambda r: r.estimated_delivery_days)
        elif strategy == SelectionStrategy.BEST_VALUE:
            ranked = sorted(rates, key=lambda r: r.price * 0.6 + r.estimated_delivery_days * 10 * 0.4)
        else:
            ranked = sorted(rates, key=lambda r: r.price)
        logger.info(f"Ranked {len(ranked)} rates using {strategy.value} strategy")
        return ranked

    def select_best(self, rates: List[RateQuote], strategy: SelectionStrategy = SelectionStrategy.CHEAPEST) -> RateQuote | None:
        """Select the best rate according to strategy."""
        ranked = self.rank_rates(rates, strategy)
        return ranked[0] if ranked else None
