"""
Carrier Agent Nodes.

Business logic steps for the carrier agent workflow.
Each node represents a discrete operation in the shipment flow.

Uses LangChain ChatLiteLLM for LLM integration and structured output.
"""

import json
import logging
import os
from typing import Any, Dict

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from orchestrator.carrier_service.agent.state import CarrierAgentState
from orchestrator.carrier_service.domain.models import ShipmentRequest
from orchestrator.carrier_service.infra.factory import CarrierFactory

logger = logging.getLogger("carrier_agent.nodes")

# LLM Configuration from environment
CARRIER_AGENT_LLM = os.getenv("CARRIER_AGENT_LLM", "openrouter/openai/gpt-4o-mini")

# System prompt for extraction
EXTRACTION_SYSTEM_PROMPT = """You are a shipping assistant that extracts shipment details from user messages.

Extract the following information from the user's message:
- origin_pincode: The origin postal/zip code (string)
- dest_pincode: The destination postal/zip code (string)  
- weight_kg: The package weight in kilograms (float)
- description: Brief description of contents (string, default to "General Goods")

If you cannot find a specific field, make a reasonable inference or use these defaults:
- If no pincodes found, use "10001" for origin and "90210" for destination
- If weight unit is in pounds/lbs, convert to kg (1 lb = 0.453592 kg)
- If no description, use "General Goods"

Respond ONLY with valid JSON in this exact format:
{
  "origin_pincode": "string",
  "dest_pincode": "string", 
  "weight_kg": number,
  "description": "string"
}"""


class CarrierNodes:
    """
    Business logic nodes for the carrier agent.

    Uses LangChain ChatLiteLLM for LLM calls with proper observability.
    """

    def __init__(self, factory: CarrierFactory):
        self.factory = factory
        # Use LangChain ChatLiteLLM for proper integration with observability
        self.llm = ChatLiteLLM(
            model=CARRIER_AGENT_LLM,
            temperature=0.1,
            max_tokens=200,
        )
        self.json_parser = JsonOutputParser()

    async def parse_request(self, state: CarrierAgentState) -> Dict[str, Any]:
        """
        Parse shipment details from user message using LLM.

        Uses LangChain ChatLiteLLM for structured output extraction.
        """
        last_msg = state["messages"][-1].content if state["messages"] else ""
        logger.info(f"Parsing request from: {last_msg[:100]}...")

        try:
            # Use LangChain LLM to extract shipment details
            parsed = await self._extract_with_llm(last_msg)
            
            if parsed:
                logger.info(f"LLM extracted: {parsed}")
                return {"request": parsed}
            else:
                return {
                    "error": "Could not parse shipment details from your request. "
                    "Please provide origin, destination, and weight.",
                    "messages": [AIMessage(content="I couldn't understand your shipping request. Please provide weight and locations.")]
                }
                    
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {
                "error": f"Failed to process request: {str(e)}",
                "messages": [AIMessage(content=f"Sorry, I encountered an error: {str(e)}")]
            }

    async def _extract_with_llm(self, message: str) -> ShipmentRequest | None:
        """
        Extract shipment details using LangChain ChatLiteLLM.
        
        Benefits of using ChatLiteLLM over direct litellm.acompletion:
        1. Automatic integration with LangChain callbacks for observability
        2. Built-in tracing with OpenTelemetry when enabled
        3. Consistent interface across LLM providers
        4. Proper async support with ainvoke()
        """
        try:
            # Create messages for the LLM
            messages = [
                SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=message)
            ]
            
            # Use LangChain's async invoke for proper tracing
            response = await self.llm.ainvoke(messages)
            
            content = response.content.strip()
            logger.debug(f"LLM response: {content}")
            
            # Parse JSON response
            # Handle markdown code blocks if present
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
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    async def fetch_rates(self, state: CarrierAgentState) -> Dict[str, Any]:
        """
        Query all carriers for rates.

        Aggregates rates from all registered carriers.
        """
        request = state.get("request")
        if not request:
            return {"error": "No shipment request to fetch rates for"}

        all_rates = []
        adapters = self.factory.get_all()

        for adapter in adapters:
            try:
                rates = await adapter.get_rates(request)
                all_rates.extend(rates)
                logger.info(f"Got {len(rates)} rates from {adapter.carrier_name}")
            except Exception as e:
                logger.error(f"Failed to fetch rates from {adapter.carrier_name}: {e}")

        if not all_rates:
            return {
                "error": "No carriers available or all carriers failed to respond",
                "messages": [AIMessage(content="Sorry, no rates are available at this time.")],
            }

        # Format rates for user display
        rate_lines = []
        for r in sorted(all_rates, key=lambda x: x.price):
            rate_lines.append(
                f"• {r.service_name} ({r.carrier.value}): "
                f"${r.price:.2f} - {r.estimated_delivery_days} days"
            )

        rate_summary = "\n".join(rate_lines)
        message = f"Found {len(all_rates)} shipping options:\n\n{rate_summary}"

        return {
            "rates": all_rates,
            "messages": [AIMessage(content=message)],
        }

    async def book_shipment(self, state: CarrierAgentState) -> Dict[str, Any]:
        """
        Book shipment with the cheapest carrier.

        Business rule: Auto-select the cheapest option.
        Production would include HITL for high-value shipments.
        """
        rates = state.get("rates", [])
        request = state.get("request")

        if not rates:
            return {
                "error": "No rates available for booking",
                "messages": [AIMessage(content="Cannot book - no rates were found.")],
            }

        if not request:
            return {
                "error": "No shipment request found",
                "messages": [AIMessage(content="Cannot book - missing shipment details.")],
            }

        # Business logic: Select cheapest rate
        best_rate = min(rates, key=lambda x: x.price)
        logger.info(f"Selected cheapest rate: {best_rate.service_name} @ ${best_rate.price}")

        try:
            adapter = self.factory.get(best_rate.carrier)
            label = await adapter.create_shipment(request, best_rate.service_code)

            message = (
                f"✅ **Shipment Booked!**\n\n"
                f"• Carrier: {best_rate.carrier.value.upper()}\n"
                f"• Service: {best_rate.service_name}\n"
                f"• Price: ${best_rate.price:.2f}\n"
                f"• Tracking: `{label.tracking_number}`\n"
                f"• Label: {label.label_url}"
            )

            return {
                "selected_rate": best_rate,
                "final_label": label,
                "messages": [AIMessage(content=message)],
            }

        except Exception as e:
            logger.error(f"Booking failed: {e}")
            return {
                "error": f"Booking failed: {str(e)}",
                "messages": [AIMessage(content=f"Booking failed: {str(e)}")],
            }
