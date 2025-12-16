"""
Supervisor Agent Tools.
"""
import logging
from langchain_core.tools import tool
from app.client import call_carrier_via_slim

logger = logging.getLogger("supervisor_agent.tools")

@tool
async def call_carrier_agent(prompt: str) -> str:
    """
    Call the Carrier Agent to check rates or book shipments.
    """
    logger.info(f"Delegating to Carrier Agent: {prompt}")
    return await call_carrier_via_slim(prompt)

SUPERVISOR_TOOLS = [call_carrier_agent]
