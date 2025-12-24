"""
Booking Agent Nodes.

Business logic nodes for order operations.
"""

import json
import logging
import os
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


from config.settings import settings
from agent.state import BookingAgentState
from agent.tools import BOOKING_TOOLS
from domain.models import ExtractedOrderIntent
from .llm_factory import LLMFactory

logger = logging.getLogger("booking_agent.nodes")


def extract_llm_error_message(error: Exception) -> str:
    """Extract a user-friendly message from LLM API errors."""
    error_str = str(error)
    
    # Check for common error patterns
    if "402" in error_str or "credits" in error_str.lower():
        return "⚠️ **API Credits Exhausted**\n\nThe AI service has run out of credits. Please try again later or contact support to add more credits."
    elif "429" in error_str or "rate limit" in error_str.lower():
        return "⚠️ **Rate Limit Reached**\n\nToo many requests. Please wait a moment and try again."
    elif "401" in error_str or "unauthorized" in error_str.lower():
        return "⚠️ **Authentication Error**\n\nThere's an issue with the AI service configuration. Please contact support."
    elif "timeout" in error_str.lower():
        return "⚠️ **Request Timeout**\n\nThe AI service took too long to respond. Please try again."
    else:
        # Generic error with some detail
        return f"⚠️ **AI Service Error**\n\nUnable to process your request: {error_str[:200]}"

BOOKING_AGENT_LLM = os.getenv("BOOKING_AGENT_LLM", settings.llm_model)

EXTRACTION_SYSTEM_PROMPT = """You are an order assistant that extracts order intent from user messages.

Determine the user's intent and extract ALL relevant details for shipping/booking:

Actions:
- "create": User wants to create/book a new order or shipment
- "get": User wants to check order status or details
- "cancel": User wants to cancel an existing order
- "list": User wants to see their orders

Extract the following information if present (null if not mentioned):

REQUIRED FOR ORDER CREATION:
- action: The action to perform (create, get, cancel, list)
- partner_code: Carrier/partner code (e.g., "shipcube", "delhivery", "aramex") - extract from carrier name if mentioned
- carrier_name: The carrier name mentioned (e.g., "ShipCube", "Delhivery")

SENDER (Origin) DETAILS:
- sender_name: Full name of sender
- sender_phone: Sender's phone number (digits only)
- origin_street: Sender's street address
- origin_city: Sender's city
- origin_state: Sender's state/province  
- origin_pincode: Origin postal/ZIP code

RECEIVER (Destination) DETAILS:
- receiver_name: Full name of receiver
- receiver_phone: Receiver's phone number (digits only)
- dest_street: Receiver's street address
- dest_city: Receiver's city
- dest_state: Receiver's state/province
- dest_pincode: Destination postal/ZIP code

PACKAGE DETAILS:
- weight_kg: Package weight in kg (number)
- length_cm: Package length in cm (number)
- width_cm: Package width in cm (number)
- height_cm: Package height in cm (number)

PAYMENT & ITEMS:
- payment_type: PREPAID, COD, or TOPAY
- item_description: Description of items being shipped

OTHER:
- order_id: Order ID if referencing existing order
- cancel_reason: Reason for cancellation if applicable

IMPORTANT RULES:
1. If user says "20 x 20 x 20" or "20x20x20", extract as length=20, width=20, height=20
2. If user mentions a carrier like "ShipCube", set partner_code="shipcube" (lowercase, no spaces)
3. Parse phone numbers as digits only (e.g., "9998887766")
4. Parse addresses carefully - separate street, city, state, pincode

Respond ONLY with valid JSON:
{
  "action": "create|get|cancel|list",
  "partner_code": "string or null",
  "carrier_name": "string or null",
  "sender_name": "string or null",
  "sender_phone": "string or null",
  "origin_street": "string or null",
  "origin_city": "string or null",
  "origin_state": "string or null",
  "origin_pincode": "string or null",
  "receiver_name": "string or null",
  "receiver_phone": "string or null",
  "dest_street": "string or null",
  "dest_city": "string or null",
  "dest_state": "string or null",
  "dest_pincode": "string or null",
  "weight_kg": number or null,
  "length_cm": number or null,
  "width_cm": number or null,
  "height_cm": number or null,
  "payment_type": "string or null",
  "item_description": "string or null",
  "order_id": "string or null",
  "cancel_reason": "string or null"
}"""


class BookingNodes:
    """Business logic nodes for order operations."""

    def __init__(self):
        self.llm = LLMFactory.get_llm(
            "BOOKING_AGENT_LLM",
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        self.tools = {t.name: t for t in BOOKING_TOOLS}

    async def parse_request(self, state: BookingAgentState) -> Dict[str, Any]:
        """Parse order intent from user message using LLM."""
        last_msg = state["messages"][-1].content if state["messages"] else ""
        logger.info(f"Parsing request from: {last_msg[:100]}...")

        try:
            intent = await self._extract_with_llm(last_msg)
            if intent:
                logger.info(f"LLM extracted intent: {intent.action}")
                return {"intent": intent}
            else:
                return {
                    "error": "Could not parse order request.",
                    "messages": [AIMessage(content="I couldn't understand your order request. Please provide more details.")],
                }
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {
                "error": f"Failed to process request: {str(e)}",
                "messages": [AIMessage(content=f"Sorry, I encountered an error: {str(e)}")],
            }

    async def _extract_with_llm(self, message: str) -> ExtractedOrderIntent | None:
        """Extract order intent using LLM."""
        try:
            messages = [
                SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
                
            data = json.loads(content)
            return ExtractedOrderIntent(
                action=data.get("action", "get"),
                order_id=data.get("order_id"),
                # Partner/Carrier
                partner_code=data.get("partner_code"),
                carrier_name=data.get("carrier_name"),
                # Sender details
                sender_name=data.get("sender_name"),
                sender_phone=data.get("sender_phone"),
                origin_street=data.get("origin_street"),
                origin_city=data.get("origin_city"),
                origin_state=data.get("origin_state"),
                origin_pincode=data.get("origin_pincode"),
                # Receiver details
                receiver_name=data.get("receiver_name"),
                receiver_phone=data.get("receiver_phone"),
                dest_street=data.get("dest_street"),
                dest_city=data.get("dest_city"),
                dest_state=data.get("dest_state"),
                dest_pincode=data.get("dest_pincode"),
                # Package details
                weight_kg=data.get("weight_kg"),
                length_cm=data.get("length_cm"),
                width_cm=data.get("width_cm"),
                height_cm=data.get("height_cm"),
                # Payment and items
                payment_type=data.get("payment_type"),
                item_description=data.get("item_description"),
                cancel_reason=data.get("cancel_reason"),
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Re-raise with user-friendly message to be caught by parse_request
            raise Exception(extract_llm_error_message(e))

    async def create_order(self, state: BookingAgentState) -> Dict[str, Any]:
        """Create a new order using the create_order tool."""
        intent = state.get("intent")
        if not intent:
            return {"error": "No order intent to process"}

        # Check retry limit to prevent infinite loops
        retry_count = state.get("retry_count", 0)
        MAX_RETRIES = 3
        if retry_count >= MAX_RETRIES:
            logger.warning(f"Max retries ({MAX_RETRIES}) reached for order creation")
            return {
                "error": f"Order creation failed after {MAX_RETRIES} attempts. Please try again later or contact support.",
                "messages": [AIMessage(content=f"I was unable to create the order after {MAX_RETRIES} attempts. The service may be temporarily unavailable. Please try again later.")],
            }

        try:
            # Generate order ID
            import uuid
            order_id = f"ORD-{str(uuid.uuid4())[:8].upper()}"
            
            # Use extracted values with sensible defaults
            sender_name = intent.sender_name or "Sender"
            sender_phone = intent.sender_phone or "9876543210"
            origin_street = intent.origin_street or "Origin Address"
            origin_city = intent.origin_city or "Mumbai"
            origin_state = intent.origin_state or "Maharashtra"
            origin_pincode = intent.origin_pincode or "400001"
            
            receiver_name = intent.receiver_name or "Receiver"
            receiver_phone = intent.receiver_phone or "9876543211"
            dest_street = intent.dest_street or "Destination Address"
            dest_city = intent.dest_city or "Delhi"
            dest_state = intent.dest_state or "Delhi"
            dest_pincode = intent.dest_pincode or "110001"
            
            weight_kg = intent.weight_kg or 1.0
            weight_grams = weight_kg * 1000
            payment_type = intent.payment_type or "PREPAID"
            item_description = intent.item_description or "General Goods"
            partner_code = intent.partner_code or "default"
            
            logger.info(f"Creating order with partner={partner_code}, from={sender_name} ({origin_pincode}) to={receiver_name} ({dest_pincode})")
            
            # Call the create order tool
            create_tool = self.tools.get("create_order")
            result = await create_tool.ainvoke({
                "order_id": order_id,
                "partner_code": partner_code,
                "origin_name": sender_name,
                "origin_phone": sender_phone,
                "origin_city": origin_city,
                "origin_state": origin_state,
                "origin_pincode": origin_pincode,
                "origin_street": origin_street,
                "dest_name": receiver_name,
                "dest_phone": receiver_phone,
                "dest_city": dest_city,
                "dest_state": dest_state,
                "dest_pincode": dest_pincode,
                "dest_street": dest_street,
                "weight_grams": weight_grams,
                "item_name": item_description,
                "item_quantity": 1,
                "item_price": 100.0,
                "payment_type": payment_type,
                "payment_amount": 100.0,
            })
            
            return {"order_response": result}
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return {
                "error": str(e),
                "retry_count": retry_count + 1,
                "messages": [AIMessage(content=f"Error creating order: {str(e)}")],
            }

    async def get_order(self, state: BookingAgentState) -> Dict[str, Any]:
        """Get order details using the get_order tool."""
        intent = state.get("intent")
        if not intent or not intent.order_id:
            return {
                "error": "No order ID provided",
                "messages": [AIMessage(content="Please provide an order ID to check its status.")],
            }

        try:
            get_tool = self.tools.get("get_order")
            result = await get_tool.ainvoke({"order_id": intent.order_id})
            return {"order_response": result}
            
        except Exception as e:
            logger.error(f"Failed to get order: {e}")
            return {
                "error": str(e),
                "messages": [AIMessage(content=f"Error fetching order: {str(e)}")],
            }

    async def cancel_order(self, state: BookingAgentState) -> Dict[str, Any]:
        """Cancel an order using the cancel_order tool."""
        intent = state.get("intent")
        if not intent or not intent.order_id:
            return {
                "error": "No order ID provided",
                "messages": [AIMessage(content="Please provide an order ID to cancel.")],
            }

        try:
            cancel_tool = self.tools.get("cancel_order")
            result = await cancel_tool.ainvoke({
                "order_id": intent.order_id,
                "reason": intent.cancel_reason or "Customer request",
                "initiated_by": "CUSTOMER",
            })
            return {"order_response": result}
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {
                "error": str(e),
                "messages": [AIMessage(content=f"Error cancelling order: {str(e)}")],
            }

    async def generate_response(self, state: BookingAgentState) -> Dict[str, Any]:
        """Generate a dynamic response using the LLM based on operation results."""
        user_msg = state["messages"][0].content
        intent = state.get("intent")
        order_response = state.get("order_response", {})
        error = state.get("error")
        
        logger.info(f"Generate response for action: {intent.action if intent else 'unknown'}")
        
        # Build context for LLM
        context = {
            "action": intent.action if intent else "unknown",
            "order_response": order_response,
            "error": error,
        }
        
        system_prompt = """You are a helpful order management assistant.
        Generate a natural, concise response based on the operation result.
        
        - If an order was created, confirm with the order ID and key details.
        - If fetching order status, summarize the order state.
        - If cancelling, confirm the cancellation.
        - If there was an error, explain it helpfully.
        
        Operation Result:
        {data}
        """
        
        messages = [
            SystemMessage(content=system_prompt.format(data=json.dumps(context, indent=2))),
            HumanMessage(content=user_msg),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"LLM error in generate_response: {e}")
            error_message = extract_llm_error_message(e)
            return {"messages": [AIMessage(content=error_message)]}
