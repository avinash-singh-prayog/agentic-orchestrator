"""
Mock Carrier APIs

Simulated carrier pricing APIs for demo purposes.
In production, these would be replaced with actual carrier API integrations.
"""

import asyncio
import random
from typing import Any


async def get_fedex_quote(
    origin: str,
    destination: str,
    weight_kg: float,
    dimensions: str = "",
) -> dict[str, Any]:
    """Simulate FedEx API call."""
    # Simulate network latency
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    base_rate = weight_kg * 2.8
    
    return {
        "carrier": "FedEx",
        "service": "International Priority",
        "price": round(base_rate * random.uniform(1.1, 1.3), 2),
        "currency": "USD",
        "estimated_days": random.choice([2, 3, 4]),
        "quote_id": f"fedex_{random.randint(10000, 99999)}",
    }


async def get_dhl_quote(
    origin: str,
    destination: str,
    weight_kg: float,
    dimensions: str = "",
) -> dict[str, Any]:
    """Simulate DHL API call."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    base_rate = weight_kg * 2.5
    
    return {
        "carrier": "DHL",
        "service": "Express Worldwide",
        "price": round(base_rate * random.uniform(1.0, 1.25), 2),
        "currency": "USD",
        "estimated_days": random.choice([3, 4, 5]),
        "quote_id": f"dhl_{random.randint(10000, 99999)}",
    }


async def get_ups_quote(
    origin: str,
    destination: str,
    weight_kg: float,
    dimensions: str = "",
) -> dict[str, Any]:
    """Simulate UPS API call."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    base_rate = weight_kg * 2.6
    
    return {
        "carrier": "UPS",
        "service": "Worldwide Express",
        "price": round(base_rate * random.uniform(1.05, 1.2), 2),
        "currency": "USD",
        "estimated_days": random.choice([3, 4, 5]),
        "quote_id": f"ups_{random.randint(10000, 99999)}",
    }


CARRIER_APIS = {
    "fedex": get_fedex_quote,
    "dhl": get_dhl_quote,
    "ups": get_ups_quote,
}
