"""
Carrier Agent Tools.

LangChain tool definitions for the carrier agent.
Tools are the interface between the LLM agent and the carrier orchestrator.
"""

import logging
from typing import Optional

from langchain_core.tools import tool

from orchestrator.carrier_service.services.carrier_orchestrator import CarrierOrchestrator
from orchestrator.carrier_service.services.carrier_selector import SelectionStrategy
from orchestrator.carrier_service.domain.models import ShipmentRequest, CarrierCode

logger = logging.getLogger("carrier_agent.tools")

# Singleton orchestrator instance
_orchestrator: Optional[CarrierOrchestrator] = None


def set_orchestrator(orchestrator: CarrierOrchestrator) -> None:
    """Set the orchestrator instance for tools to use."""
    global _orchestrator
    _orchestrator = orchestrator
    logger.info("Orchestrator injected into tools")


def get_orchestrator() -> CarrierOrchestrator:
    """Get the orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CarrierOrchestrator()
    return _orchestrator


@tool
async def check_serviceability(origin: str, destination: str) -> dict:
    """
    Check if shipping is available between origin and destination pincodes.
    
    Args:
        origin: Origin postal/pin code (e.g., "411001")
        destination: Destination postal/pin code (e.g., "700001")
    """
    orchestrator = get_orchestrator()
    results = await orchestrator.check_serviceability_all(origin, destination)
    return {
        "origin": origin,
        "destination": destination,
        "carriers": [{"carrier": r.carrier.value, "is_serviceable": r.is_serviceable, "message": r.message} for r in results],
        "serviceable_count": sum(1 for r in results if r.is_serviceable),
    }


@tool
async def get_shipping_rates(origin: str, destination: str, weight_kg: float, description: str = "General Goods", strategy: str = "cheapest") -> dict:
    """
    Get shipping rates from all available carriers.
    
    Args:
        origin: Origin postal/pin code
        destination: Destination postal/pin code
        weight_kg: Package weight in kilograms
        description: Brief description of contents
        strategy: Ranking strategy - "cheapest", "fastest", or "best_value"
    """
    orchestrator = get_orchestrator()
    request = ShipmentRequest(origin_pincode=origin, dest_pincode=destination, weight_kg=weight_kg, description=description)
    strategy_enum = SelectionStrategy(strategy) if strategy in ["cheapest", "fastest", "best_value"] else SelectionStrategy.CHEAPEST
    rates = await orchestrator.get_best_rates(request, strategy_enum)
    return {
        "request": {"origin": origin, "destination": destination, "weight_kg": weight_kg},
        "strategy": strategy_enum.value,
        "rates": [{"carrier": r.carrier.value, "service_name": r.service_name, "service_code": r.service_code, "price": r.price, "currency": r.currency, "estimated_days": r.estimated_delivery_days} for r in rates],
        "total_options": len(rates),
    }


@tool
async def create_shipment(carrier: str, service_code: str, origin: str, destination: str, weight_kg: float, description: str = "General Goods") -> dict:
    """
    Book a shipment with a specific carrier and service.
    
    Args:
        carrier: Carrier code (e.g., "mock", "dhl")
        service_code: Service code from rate quote (e.g., "MOCK_STD")
        origin: Origin postal/pin code
        destination: Destination postal/pin code
        weight_kg: Package weight in kilograms
        description: Brief description of contents
    """
    orchestrator = get_orchestrator()
    request = ShipmentRequest(origin_pincode=origin, dest_pincode=destination, weight_kg=weight_kg, description=description)
    carrier_code = CarrierCode(carrier.lower())
    label = await orchestrator.create_shipment(carrier_code, request, service_code)
    return {"success": True, "tracking_number": label.tracking_number, "label_url": label.label_url, "carrier": label.carrier.value}


@tool
async def create_shipment_auto(origin: str, destination: str, weight_kg: float, description: str = "General Goods", strategy: str = "cheapest") -> dict:
    """
    Automatically select the best carrier and create a shipment.
    
    Args:
        origin: Origin postal/pin code
        destination: Destination postal/pin code
        weight_kg: Package weight in kilograms
        description: Brief description of contents
        strategy: Selection strategy - "cheapest", "fastest", or "best_value"
    """
    orchestrator = get_orchestrator()
    request = ShipmentRequest(origin_pincode=origin, dest_pincode=destination, weight_kg=weight_kg, description=description)
    strategy_enum = SelectionStrategy(strategy) if strategy in ["cheapest", "fastest", "best_value"] else SelectionStrategy.CHEAPEST
    label, rate = await orchestrator.create_shipment_auto(request, strategy_enum)
    return {
        "success": True, "tracking_number": label.tracking_number, "label_url": label.label_url,
        "carrier": label.carrier.value, "selected_service": rate.service_name, "price": rate.price,
        "currency": rate.currency, "estimated_days": rate.estimated_delivery_days, "strategy_used": strategy_enum.value,
    }


# Export all tools
CARRIER_TOOLS = [check_serviceability, get_shipping_rates, create_shipment, create_shipment_auto]
