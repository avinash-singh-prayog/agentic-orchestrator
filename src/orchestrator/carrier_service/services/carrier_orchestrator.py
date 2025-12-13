"""
Carrier Orchestrator.

Orchestrates operations across multiple carrier adapters.
This is the main entry point for agent tools to interact with carriers.
"""

import asyncio
import logging
from typing import List, Optional

from orchestrator.carrier_service.services.carriers.factory import CarrierFactory
from orchestrator.carrier_service.domain.models import (
    CarrierType, LabelResponse, RateQuote, ServiceabilityResult, ShipmentRequest,
)
from orchestrator.carrier_service.services.carrier_selector import CarrierSelector, SelectionStrategy

logger = logging.getLogger("carrier.orchestrator")


class CarrierOrchestrator:
    """
    Orchestrates multi-carrier operations.
    
    Handles parallel calls to carriers, rate aggregation, and error isolation.
    """

    def __init__(self, factory: Optional[CarrierFactory] = None, selector: Optional[CarrierSelector] = None):
        self.factory = factory or CarrierFactory()
        self.selector = selector or CarrierSelector()
        logger.info(f"Initialized orchestrator with {len(self.factory.get_all())} carriers")

    async def check_serviceability_all(self, origin: str, destination: str) -> List[ServiceabilityResult]:
        """Check serviceability across all carriers in parallel."""
        carriers = self.factory.get_all()

        async def check_carrier(adapter):
            try:
                return await adapter.check_serviceability(origin, destination)
            except Exception as e:
                logger.error(f"Serviceability check failed for {adapter.carrier_name}: {e}")
                return None

        results = await asyncio.gather(*[check_carrier(c) for c in carriers], return_exceptions=True)
        valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]
        logger.info(f"Checked serviceability: {len(valid_results)}/{len(carriers)} carriers responded")
        return valid_results

    async def get_rates_all(self, request: ShipmentRequest) -> List[RateQuote]:
        """Get rates from all carriers in parallel."""
        carriers = self.factory.get_all()

        async def fetch_rates(adapter):
            try:
                return await adapter.get_rates(request)
            except Exception as e:
                logger.error(f"Rate fetch failed for {adapter.carrier_name}: {e}")
                return []

        results = await asyncio.gather(*[fetch_rates(c) for c in carriers], return_exceptions=True)
        all_rates = []
        for result in results:
            if isinstance(result, list):
                all_rates.extend(result)
        logger.info(f"Fetched {len(all_rates)} rates from {len(carriers)} carriers")
        return all_rates

    async def get_best_rates(self, request: ShipmentRequest, strategy: SelectionStrategy = SelectionStrategy.CHEAPEST) -> List[RateQuote]:
        """Get rates ranked by strategy."""
        all_rates = await self.get_rates_all(request)
        return self.selector.rank_rates(all_rates, strategy)

    async def create_shipment(self, carrier_type: CarrierType, request: ShipmentRequest, service_code: str) -> LabelResponse:
        """Create a shipment with a specific carrier."""
        adapter = self.factory.get(carrier_type)
        logger.info(f"Creating shipment with {adapter.carrier_name}")
        return await adapter.create_shipment(request, service_code)

    async def create_shipment_auto(self, request: ShipmentRequest, strategy: SelectionStrategy = SelectionStrategy.CHEAPEST) -> tuple[LabelResponse, RateQuote]:
        """Auto-select best carrier and create shipment."""
        rates = await self.get_best_rates(request, strategy)
        if not rates:
            raise ValueError("No carriers available for this shipment")
        best_rate = rates[0]
        logger.info(f"Auto-selected: {best_rate.service_name} @ ${best_rate.price} ({best_rate.carrier.value})")
        label = await self.create_shipment(best_rate.carrier, request, best_rate.service_code)
        return label, best_rate
