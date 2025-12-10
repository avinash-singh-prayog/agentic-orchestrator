"""
LangChain Tools for the Supervisor Agent

These tools enable the supervisor to interact with worker agents
and external services. Uses Python 3.14 t-strings for prompt safety.
"""

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ===========================
# Serviceability Tools
# ===========================

@tool
async def check_serviceability(
    origin: str,
    destination: str,
    shipment_type: str = "standard",
) -> dict[str, Any]:
    """
    Check if a shipping route is serviceable.
    
    Validates:
    - Address validity for origin and destination
    - Route availability
    - Embargo/restriction checks
    - Carrier coverage
    
    Args:
        origin: Origin address or location code.
        destination: Destination address or location code.
        shipment_type: Type of shipment (standard, express, freight).
        
    Returns:
        Dictionary with serviceability status and details.
    """
    logger.info(f"Checking serviceability: {origin} -> {destination}")
    
    # In production, this would call the Serviceability Agent via A2A
    # For now, return mock response
    
    # Simulate validation logic
    is_serviceable = True
    reasons = []
    
    # Check for known unserviceable routes (mock)
    blocked_countries = ["North Korea", "Iran", "Syria"]
    if any(country.lower() in destination.lower() for country in blocked_countries):
        is_serviceable = False
        reasons.append("Destination is under trade embargo")
    
    return {
        "is_serviceable": is_serviceable,
        "origin": origin,
        "destination": destination,
        "shipment_type": shipment_type,
        "reasons": reasons,
        "available_carriers": ["FedEx", "DHL", "UPS"] if is_serviceable else [],
    }


# ===========================
# Rate Negotiation Tools
# ===========================

@tool
async def get_shipping_rates(
    origin: str,
    destination: str,
    weight_kg: float,
    dimensions: str = "",
    shipment_type: str = "standard",
) -> dict[str, Any]:
    """
    Get shipping rate quotes from multiple carriers.
    
    Queries carrier pricing engines and returns aggregated quotes.
    
    Args:
        origin: Origin address.
        destination: Destination address.
        weight_kg: Total weight in kilograms.
        dimensions: Dimensions in LxWxH cm format.
        shipment_type: Type of shipment.
        
    Returns:
        Dictionary with quotes from available carriers.
    """
    logger.info(f"Getting rates: {origin} -> {destination}, {weight_kg}kg")
    
    # In production, this would call the Rate Agent via A2A
    # Using asyncio.TaskGroup for parallel carrier queries
    
    # Mock carrier quotes
    base_rate = weight_kg * 2.5
    
    quotes = [
        {
            "carrier": "FedEx",
            "service": "International Priority",
            "price": round(base_rate * 1.2, 2),
            "currency": "USD",
            "estimated_days": 3,
            "quote_id": "fedex_quote_001",
        },
        {
            "carrier": "DHL",
            "service": "Express Worldwide",
            "price": round(base_rate * 1.15, 2),
            "currency": "USD",
            "estimated_days": 4,
            "quote_id": "dhl_quote_001",
        },
        {
            "carrier": "UPS",
            "service": "Worldwide Express",
            "price": round(base_rate * 1.1, 2),
            "currency": "USD",
            "estimated_days": 5,
            "quote_id": "ups_quote_001",
        },
    ]
    
    return {
        "origin": origin,
        "destination": destination,
        "weight_kg": weight_kg,
        "quotes": quotes,
        "best_price": min(quotes, key=lambda q: q["price"]),
        "fastest": min(quotes, key=lambda q: q["estimated_days"]),
    }


# ===========================
# Booking Tools
# ===========================

@tool
async def book_shipment(
    quote_id: str,
    order_id: str,
    customer_id: str,
    order_value: float,
) -> dict[str, Any]:
    """
    Book a shipment with the selected carrier.
    
    This action may trigger Human-in-the-Loop (HITL) approval
    if the order value exceeds the auto-approval threshold.
    
    Args:
        quote_id: The selected quote identifier.
        order_id: The order identifier.
        customer_id: Customer identifier.
        order_value: Total value of the order in USD.
        
    Returns:
        Dictionary with booking confirmation or pending approval status.
    """
    logger.info(f"Booking shipment: quote={quote_id}, order={order_id}, value=${order_value}")
    
    # In production, this would:
    # 1. Check with Identity Service if approval is needed
    # 2. If approval needed, trigger HITL interrupt
    # 3. Call Carrier Agent to execute booking
    
    # Mock response
    from orchestrator.common.config import settings
    
    needs_approval = order_value > settings.max_auto_approval_limit
    
    if needs_approval:
        return {
            "status": "pending_approval",
            "order_id": order_id,
            "quote_id": quote_id,
            "order_value": order_value,
            "message": f"Order value (${order_value}) exceeds auto-approval limit (${settings.max_auto_approval_limit}). Human approval required.",
            "approval_request_id": f"approval_{order_id}",
        }
    
    # Auto-approved booking
    from uuid import uuid4
    
    return {
        "status": "confirmed",
        "order_id": order_id,
        "quote_id": quote_id,
        "booking_id": f"BK{uuid4().hex[:10].upper()}",
        "tracking_number": f"TRK{uuid4().hex[:12].upper()}",
        "carrier": "FedEx",  # Would be determined from quote_id
        "message": "Shipment booked successfully",
    }


# ===========================
# Tool Registry
# ===========================

SUPERVISOR_TOOLS = [
    check_serviceability,
    get_shipping_rates,
    book_shipment,
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """
    Get OpenAI-compatible tool definitions.
    
    Returns:
        List of tool definitions for function calling.
    """
    definitions = []
    
    for tool_fn in SUPERVISOR_TOOLS:
        definitions.append({
            "type": "function",
            "function": {
                "name": tool_fn.name,
                "description": tool_fn.description,
                "parameters": tool_fn.args_schema.schema() if hasattr(tool_fn, "args_schema") else {},
            },
        })
    
    return definitions
