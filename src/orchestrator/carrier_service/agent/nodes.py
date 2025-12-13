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

from orchestrator.carrier_service.agent.state import CarrierAgentState
from orchestrator.carrier_service.agent.tools import get_shipping_rates, create_shipment_auto
from orchestrator.carrier_service.domain.models import ShipmentRequest

logger = logging.getLogger("carrier_agent.nodes")

CARRIER_AGENT_LLM = os.getenv("CARRIER_AGENT_LLM", "openrouter/openai/gpt-4o-mini")

EXTRACTION_SYSTEM_PROMPT = """You are a shipping assistant that extracts shipment details from user messages.

Extract the following information:
- origin_pincode: The origin postal/zip code (string)
- dest_pincode: The destination postal/zip code (string)  
- weight_kg: The package weight in kilograms (float)
- description: Brief description of contents (string, default to "General Goods")

If you cannot find a specific field, make a reasonable inference or use defaults.

Respond ONLY with valid JSON:
{
  "origin_pincode": "string",
  "dest_pincode": "string", 
  "weight_kg": number,
  "description": "string"
}"""


class CarrierNodes:
    """Business logic nodes using tools to interact with carriers."""

    def __init__(self):
        self.llm = ChatLiteLLM(model=CARRIER_AGENT_LLM, temperature=0.1, max_tokens=200)
        self.json_parser = JsonOutputParser()

    async def parse_request(self, state: CarrierAgentState) -> Dict[str, Any]:
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
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    async def fetch_rates(self, state: CarrierAgentState) -> Dict[str, Any]:
        """Fetch rates using the get_shipping_rates tool."""
        request = state.get("request")
        if not request:
            return {"error": "No shipment request to fetch rates for"}

        try:
            # Use the tool to get rates
            result = await get_shipping_rates.ainvoke({
                "origin": request.origin_pincode,
                "destination": request.dest_pincode,
                "weight_kg": request.weight_kg,
                "description": request.description,
                "strategy": "cheapest",
            })
            
            rates_data = result.get("rates", [])
            if not rates_data:
                return {
                    "error": "No carriers available",
                    "messages": [AIMessage(content="Sorry, no rates are available at this time.")],
                }

            # Format rates for display
            rate_lines = [f"• {r['service_name']} ({r['carrier']}): ${r['price']:.2f} - {r['estimated_days']} days" for r in rates_data]
            message = f"Found {len(rates_data)} shipping options:\n\n" + "\n".join(rate_lines)
            
            return {"rates": rates_data, "messages": [AIMessage(content=message)]}

        except Exception as e:
            logger.error(f"Failed to fetch rates: {e}")
            return {"error": str(e), "messages": [AIMessage(content=f"Error fetching rates: {str(e)}")]}

    async def book_shipment(self, state: CarrierAgentState) -> Dict[str, Any]:
        """Book shipment using the create_shipment_auto tool."""
        request = state.get("request")
        rates = state.get("rates", [])

        if not rates:
            return {"error": "No rates available", "messages": [AIMessage(content="Cannot book - no rates were found.")]}
        if not request:
            return {"error": "No shipment request", "messages": [AIMessage(content="Cannot book - missing shipment details.")]}

        try:
            # Use the tool to auto-book with cheapest option
            result = await create_shipment_auto.ainvoke({
                "origin": request.origin_pincode,
                "destination": request.dest_pincode,
                "weight_kg": request.weight_kg,
                "description": request.description,
                "strategy": "cheapest",
            })

            message = (
                f"✅ **Shipment Booked!**\n\n"
                f"• Carrier: {result['carrier'].upper()}\n"
                f"• Service: {result['selected_service']}\n"
                f"• Price: ${result['price']:.2f}\n"
                f"• Tracking: `{result['tracking_number']}`\n"
                f"• Label: {result['label_url']}"
            )

            return {
                "selected_rate": result,
                "final_label": result,
                "messages": [AIMessage(content=message)],
            }

        except Exception as e:
            logger.error(f"Booking failed: {e}")
            return {"error": f"Booking failed: {str(e)}", "messages": [AIMessage(content=f"Booking failed: {str(e)}")]}
