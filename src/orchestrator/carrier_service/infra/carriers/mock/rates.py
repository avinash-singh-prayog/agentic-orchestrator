"""
Mock Carrier - Rate Fetching.

Simulates rate fetching for testing purposes.
"""

import asyncio
import logging
from typing import List

from orchestrator.carrier_service.domain.models import (
    CarrierType,
    RateQuote,
    ShipmentRequest,
)

logger = logging.getLogger("carrier.mock.rates")


class MockRateFetcher:
    """Mock implementation of rate fetching."""

    # Service tiers with base prices
    SERVICE_TIERS = [
        {
            "name": "Standard Ground",
            "code": "MOCK_STD",
            "base_price": 10.0,
            "days": 5,
        },
        {
            "name": "Express",
            "code": "MOCK_EXP",
            "base_price": 20.0,
            "days": 2,
        },
        {
            "name": "Priority Air",
            "code": "MOCK_PRI",
            "base_price": 35.0,
            "days": 1,
        },
    ]

    async def get_rates(self, request: ShipmentRequest) -> List[RateQuote]:
        """
        Fetch rates for a shipment.

        For mock: Returns fixed service tiers with prices based on weight.
        """
        # Simulate network latency
        await asyncio.sleep(0.3)

        rates = []
        for tier in self.SERVICE_TIERS:
            # Calculate price based on weight
            price = tier["base_price"] * request.weight_kg

            # Add dimensional weight surcharge if dimensions provided
            if all([request.length_cm, request.width_cm, request.height_cm]):
                dim_weight = (
                    request.length_cm * request.width_cm * request.height_cm
                ) / 5000  # DIM factor
                if dim_weight > request.weight_kg:
                    price = tier["base_price"] * dim_weight

            rates.append(
                RateQuote(
                    carrier=CarrierType.MOCK,
                    service_name=tier["name"],
                    service_code=tier["code"],
                    price=round(price, 2),
                    currency="USD",
                    estimated_delivery_days=tier["days"],
                )
            )

        logger.info(
            f"Fetched {len(rates)} rates for {request.weight_kg}kg shipment"
        )

        return rates
