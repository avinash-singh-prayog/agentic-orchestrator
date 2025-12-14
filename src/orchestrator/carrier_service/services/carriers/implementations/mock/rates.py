"""Mock Carrier - Rate Fetching."""

import asyncio
import logging
from typing import List

from orchestrator.carrier_service.domain.models import CarrierCode, RateQuote, ShipmentRequest

logger = logging.getLogger("carrier.mock.rates")


class MockRateFetcher:
    """Mock implementation of rate fetching."""

    SERVICE_TIERS = [
        {"name": "Standard Ground", "code": "MOCK_STD", "base_price": 10.0, "days": 5},
        {"name": "Express", "code": "MOCK_EXP", "base_price": 20.0, "days": 2},
        {"name": "Priority Air", "code": "MOCK_PRI", "base_price": 35.0, "days": 1},
    ]

    async def get_rates(self, request: ShipmentRequest) -> List[RateQuote]:
        await asyncio.sleep(0.3)
        rates = []
        for tier in self.SERVICE_TIERS:
            price = tier["base_price"] * request.weight_kg
            if all([request.length_cm, request.width_cm, request.height_cm]):
                dim_weight = (request.length_cm * request.width_cm * request.height_cm) / 5000
                if dim_weight > request.weight_kg:
                    price = tier["base_price"] * dim_weight
            rates.append(RateQuote(
                carrier=CarrierCode.MOCK, service_name=tier["name"], service_code=tier["code"],
                price=round(price, 2), currency="USD", estimated_delivery_days=tier["days"],
            ))
        logger.info(f"Fetched {len(rates)} rates for {request.weight_kg}kg shipment")
        return rates
