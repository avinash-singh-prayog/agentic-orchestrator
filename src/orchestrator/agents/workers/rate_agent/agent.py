"""
Rate Agent

Aggregates shipping rate quotes from multiple carriers using
parallel async queries for optimal performance.
"""

import asyncio
import logging
from typing import Any

from orchestrator.agents.workers.rate_agent.mock_carriers import CARRIER_APIS
from orchestrator.common.llm import get_llm_provider

logger = logging.getLogger(__name__)


class RateAgent:
    """
    Rate negotiation agent.
    
    Queries multiple carrier pricing APIs in parallel using
    asyncio.TaskGroup for optimal performance.
    
    This is a stateless agent designed for horizontal scalability.
    """
    
    def __init__(self):
        """Initialize the rate agent."""
        self._llm = get_llm_provider(agent_type="rate")
        logger.info("Initialized RateAgent")
    
    async def ainvoke(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Get rate quotes from all carriers.
        
        Args:
            request: Dictionary with 'origin', 'destination', 'weight_kg'.
            
        Returns:
            Dictionary with quotes from all carriers and recommendations.
        """
        origin = request.get("origin", "")
        destination = request.get("destination", "")
        weight_kg = request.get("weight_kg", 10.0)
        dimensions = request.get("dimensions", "")
        
        logger.info(f"Getting rates: {origin} -> {destination}, {weight_kg}kg")
        
        # Query all carriers in parallel
        quotes = await self._query_all_carriers(origin, destination, weight_kg, dimensions)
        
        # Analyze and recommend
        if quotes:
            best_price = min(quotes, key=lambda q: q["price"])
            fastest = min(quotes, key=lambda q: q["estimated_days"])
            best_value = self._calculate_best_value(quotes)
        else:
            best_price = None
            fastest = None
            best_value = None
        
        return {
            "origin": origin,
            "destination": destination,
            "weight_kg": weight_kg,
            "quotes": quotes,
            "best_price": best_price,
            "fastest": fastest,
            "best_value": best_value,
            "quote_count": len(quotes),
        }
    
    async def _query_all_carriers(
        self,
        origin: str,
        destination: str,
        weight_kg: float,
        dimensions: str,
    ) -> list[dict[str, Any]]:
        """Query all carriers in parallel using TaskGroup."""
        quotes = []
        
        async with asyncio.TaskGroup() as tg:
            tasks = {
                carrier: tg.create_task(
                    api_func(origin, destination, weight_kg, dimensions)
                )
                for carrier, api_func in CARRIER_APIS.items()
            }
        
        # Collect results
        for carrier, task in tasks.items():
            try:
                result = task.result()
                quotes.append(result)
                logger.debug(f"Got quote from {carrier}: ${result['price']}")
            except Exception as e:
                logger.warning(f"Failed to get quote from {carrier}: {e}")
        
        return quotes
    
    def _calculate_best_value(self, quotes: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Calculate best value (price/speed ratio)."""
        if not quotes:
            return None
        
        # Score = price / days (lower is better)
        # Normalize to find best balance
        for quote in quotes:
            quote["value_score"] = quote["price"] / quote["estimated_days"]
        
        return min(quotes, key=lambda q: q.get("value_score", float("inf")))
