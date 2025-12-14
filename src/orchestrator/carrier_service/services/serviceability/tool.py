"""
Serviceability Tool.

LangChain tool for checking serviceability and rates via the internal API.
"""

from typing import Type, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from orchestrator.carrier_service.services.serviceability.client import ServiceabilityClient

class ServiceabilityInput(BaseModel):
    """Input for serviceability check."""
    origin_pincode: str = Field(..., description="Origin postal/pin code (e.g. '400001')")
    dest_pincode: str = Field(..., description="Destination postal/pin code (e.g. '10001')")
    weight_kg: float = Field(default=1.0, description="Weight in kg")
    country_code_origin: str = Field(default="IN", description="Origin Country Code (ISO 2-letter)")
    country_code_dest: str = Field(default="IN", description="Destination Country Code (ISO 2-letter)")

@tool("check_serviceability", args_schema=ServiceabilityInput)
async def check_serviceability_tool(
    origin_pincode: str,
    dest_pincode: str,
    weight_kg: float = 1.0,
    country_code_origin: str = "IN",
    country_code_dest: str = "IN"
) -> dict:
    """
    Check serviceability and get rates from available partners.
    
    Returns a list of partners with their serviceability status and available rates.
    Use this tool when you need to find out which carriers can ship to a destination or to get shipping costs.
    """
    client = ServiceabilityClient()
    response = await client.check_serviceability(
        origin_pincode=origin_pincode,
        dest_pincode=dest_pincode,
        origin_country=country_code_origin,
        dest_country=country_code_dest,
        weight_kg=weight_kg
    )
    
    # Return the raw model or a dict. LangChain tools usually work well with dicts.
    return response.model_dump()
