"""
Supervisor Agent Tools.
"""
import logging
from langchain_core.tools import tool

# Import from app.client - this module is in agent/, client is in app/
import sys
import os

# Add parent directory to path for cross-package import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.client import call_serviceability_via_slim
from app.booking_client import call_booking_via_slim

logger = logging.getLogger("supervisor_agent.tools")

@tool
async def call_serviceability_agent(prompt: str) -> str:
    """
    Call the Serviceability Agent to check rates or serviceability.
    Use this when the user asks about shipping rates, carrier availability, or serviceability.
    """
    logger.info(f"Delegating to Serviceability Agent: {prompt}")
    return await call_serviceability_via_slim(prompt)


@tool
async def call_booking_agent(prompt: str) -> str:
    """
    Call the Booking Agent to create, retrieve, or cancel orders.
    Use this when the user wants to book a shipment, check order status, or cancel an order.
    """
    logger.info(f"Delegating to Booking Agent: {prompt}")
    return await call_booking_via_slim(prompt)


SUPERVISOR_TOOLS = [call_serviceability_agent, call_booking_agent]

