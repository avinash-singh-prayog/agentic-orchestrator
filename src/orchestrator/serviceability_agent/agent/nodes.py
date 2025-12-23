"""
Carrier Agent Nodes.

Business logic nodes that use tools to interact with carriers.
"""

import json
import logging
import os
from typing import Any, Dict

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from config.settings import settings
from agent.state import ServiceabilityAgentState
from agent.tools import check_serviceability_tool
from domain.models import ShipmentRequest, RateQuote, LabelResponse, PartnerCode

logger = logging.getLogger("serviceability_agent.nodes")

# Commented out: openai/gpt-4o-mini - use openai/gpt-oss-120b:free instead
# SERVICEABILITY_AGENT_LLM = os.getenv("SERVICEABILITY_AGENT_LLM", "openrouter/openai/gpt-4o-mini")
SERVICEABILITY_AGENT_LLM = os.getenv("SERVICEABILITY_AGENT_LLM")  # Must be set in environment

EXTRACTION_SYSTEM_PROMPT = """You are a shipping assistant that extracts shipment details from user messages.

Extract the following information:
- origin_pincode: The origin postal/zip code (string)
- dest_pincode: The destination postal/zip code (string)  
- weight_kg: The package weight in kilograms (float)
- description: Brief description of contents (string, default to "General Goods")
- origin_country: Origin country ISO code (string, default "IN")
- dest_country: Destination country ISO code (string, default "IN")

If the user mentions "US", "USA", "America", defaulting dest_country to "US" is reasonable.
If the zip code looks like a US zip (5 digits) and user mentions international context, assume US.

Respond ONLY with valid JSON:
{
  "origin_pincode": "string",
  "dest_pincode": "string", 
  "weight_kg": number,
  "description": "string",
  "origin_country": "string",
  "dest_country": "string"
}"""


class ServiceabilityNodes:
    """Business logic nodes using tools to interact with carriers."""

    def __init__(self):
        self.llm = ChatLiteLLM(model=SERVICEABILITY_AGENT_LLM, temperature=0.1, max_tokens=200)
        self.json_parser = JsonOutputParser()

    async def parse_request(self, state: ServiceabilityAgentState) -> Dict[str, Any]:
        """Parse shipment details from user message using LLM."""
        last_msg = state["messages"][-1].content if state["messages"] else ""
        logger.info(f"Parsing request from: {last_msg[:100]}...")

        try:
            parsed = await self._extract_with_llm(last_msg)
            if parsed:
                logger.info(f"LLM extracted: {parsed}")
                return {"request": parsed}
            else:
                return {
                    "error": "Could not parse shipment details.",
                    "messages": [AIMessage(content="I couldn't understand your shipping request. Please provide weight and locations.")]
                }
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {"error": f"Failed to process request: {str(e)}", "messages": [AIMessage(content=f"Sorry, I encountered an error: {str(e)}")]}

    async def _extract_with_llm(self, message: str) -> ShipmentRequest | None:
        """Extract shipment details using LLM."""
        try:
            messages = [SystemMessage(content=EXTRACTION_SYSTEM_PROMPT), HumanMessage(content=message)]
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            data = json.loads(content)
            return ShipmentRequest(
                origin_pincode=str(data.get("origin_pincode", "10001")),
                dest_pincode=str(data.get("dest_pincode", "90210")),
                weight_kg=float(data.get("weight_kg", 1.0)),
                description=str(data.get("description", "General Goods")),
                origin_country=str(data.get("origin_country", "IN")),
                dest_country=str(data.get("dest_country", "IN")),
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    async def fetch_rates(self, state: ServiceabilityAgentState) -> Dict[str, Any]:
        """Fetch rates using the check_serviceability_tool (which includes rates)."""
        request = state.get("request")
        if not request:
            return {"error": "No shipment request to fetch rates for"}

        try:
            # Use the serviceability tool to get partners and rates
            # Note: The tool returns a dictionary (model_dump)
            result = await check_serviceability_tool.ainvoke({
                "origin_pincode": request.origin_pincode,
                "dest_pincode": request.dest_pincode,
                "weight_kg": request.weight_kg,
                "country_code_origin": request.origin_country,
                "country_code_dest": request.dest_country
            })
            
            partners = result.get("partners", [])
            rates_data = []

            # Extract rates from partners structure
            for partner in partners:
                if not partner.get("is_serviceable"):
                    continue
                
                partner_name = partner.get("partner_name", "Unknown")
                for service in partner.get("services", []):
                    rate_info = service.get("rate")
                    if rate_info and rate_info.get("price"):
                        price = rate_info["price"].get("amount", 0)
                        currency = rate_info["price"].get("currency", "INR")
                        rates_data.append({
                            "carrier": partner_name,
                            "service_name": service.get("service_name"),
                            "service_code": service.get("service_code"),
                            "price": price,
                            "currency": currency,
                            "estimated_days": service.get("tat_days", 0)
                        })

            # Store raw result for generation
            
            return {
                "rates": rates_data, 
                "serviceability_response": result,
                # Do NOT return a final message here, let generate_response handle it
            }

        except Exception as e:
            logger.error(f"Failed to fetch rates: {e}")
            return {"error": str(e), "messages": [AIMessage(content=f"Error fetching rates: {str(e)}")]}

    async def generate_response(self, state: ServiceabilityAgentState) -> Dict[str, Any]:
        """Generate a dynamic response using the LLM based on tool outputs."""
        user_msg = state["messages"][0].content
        data = state.get("serviceability_response", {})
        partners = data.get("partners", [])
        logger.info(f"Generate response context: Found {len(partners)} partners")
        
        # lightweight context to save tokens
        context = {
            "partners": partners,
            "metadata": data.get("metadata", {})
        }
        
        system_prompt = """You are a helpful logistics assistant.
        Answer the user's question based strictly on the provided serviceability data.
        
        - If the user asks for available carriers, list them.
        - If the user asks for the cheapest, find it in the data.
        - If the user asks for the fastest, find it in the data.
        - Use the specific prices and currency from the data.
        - Be concise and natural.
        
        Data:
        {data}
        """
        
        messages = [
            SystemMessage(content=system_prompt.format(data=json.dumps(context, indent=2))),
            HumanMessage(content=user_msg)
        ]
        
        response = await self.llm.ainvoke(messages)
        return {"messages": [response]}

    async def book_shipment(self, state: ServiceabilityAgentState) -> Dict[str, Any]:
        """Book shipment Stub."""
        # Booking logic is pending migration to the new toolset.
        # Returning a placeholder message.
        return {
             "messages": [AIMessage(content="✅ **Booking capability is currently being upgraded.**\n\nPlease use the external booking portal for now.")]
        }
