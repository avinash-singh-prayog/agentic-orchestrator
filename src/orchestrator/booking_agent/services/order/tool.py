"""
Order LangChain Tools.

LangChain tools for order operations in LangGraph workflow.
"""

from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.order.client import OrderClient
from domain.models import (
    OrderRequest,
    CancelRequest,
    Address,
    AddressType,
    Shipment,
    PackageItem,
    Payment,
    PaymentType,
    PaymentStatus,
    CancelInitiator,
    Partner,
    OrderMetadata,
)


class CreateOrderInput(BaseModel):
    """Input for creating an order."""
    order_id: str = Field(..., description="Unique order identifier")
    partner_code: str = Field(default="smile_hubops", description="Partner/carrier code")
    origin_name: str = Field(..., description="Sender/pickup contact name")
    origin_phone: str = Field(..., description="Sender phone number")
    origin_city: str = Field(..., description="Origin city")
    origin_state: str = Field(..., description="Origin state")
    origin_pincode: str = Field(..., description="Origin postal/ZIP code")
    origin_street: str = Field(default="", description="Origin street address")
    dest_name: str = Field(..., description="Receiver/delivery contact name")
    dest_phone: str = Field(..., description="Receiver phone number")
    dest_city: str = Field(..., description="Destination city")
    dest_state: str = Field(..., description="Destination state")
    dest_pincode: str = Field(..., description="Destination postal/ZIP code")
    dest_street: str = Field(default="", description="Destination street address")
    weight_grams: float = Field(..., description="Package weight in grams")
    item_name: str = Field(default="General Goods", description="Item description")
    item_quantity: int = Field(default=1, description="Item quantity")
    item_price: float = Field(default=100.0, description="Item price")
    payment_type: str = Field(default="PREPAID", description="PREPAID, COD, or TOPAY")
    payment_amount: float = Field(..., description="Total payment amount")


class GetOrderInput(BaseModel):
    """Input for getting order details."""
    order_id: str = Field(..., description="Order ID to retrieve")


class CancelOrderInput(BaseModel):
    """Input for cancelling an order."""
    order_id: str = Field(..., description="Order ID to cancel")
    reason: str = Field(..., description="Cancellation reason")
    initiated_by: str = Field(default="CUSTOMER", description="Who initiated: CUSTOMER, MERCHANT, or SYSTEM")


@tool("create_order", args_schema=CreateOrderInput)
async def create_order_tool(
    order_id: str,
    origin_name: str,
    origin_phone: str,
    origin_city: str,
    origin_state: str,
    origin_pincode: str,
    origin_street: str,
    dest_name: str,
    dest_phone: str,
    dest_city: str,
    dest_state: str,
    dest_pincode: str,
    dest_street: str,
    weight_grams: float,
    item_name: str,
    item_quantity: int,
    item_price: float,
    payment_type: str,
    payment_amount: float,
    partner_code: str = "smile_hubops",
) -> dict:
    """
    Create a new shipping order.
    
    Use this tool when the user wants to book a shipment or create an order.
    Requires origin and destination addresses, package weight, and payment details.
    """
    # Build addresses - all 4 types
    origin_street_addr = origin_street or f"{origin_city} Main Road"
    dest_street_addr = dest_street or f"{dest_city} Main Road"
    origin_address_name = f"{origin_street_addr}, {origin_city}, {origin_pincode}, {origin_state}, India"
    dest_address_name = f"{dest_street_addr}, {dest_city}, {dest_pincode}, {dest_state}, India"
    
    addresses = [
        Address(
            type=AddressType.PICKUP,
            name=origin_name,
            phone=origin_phone,
            city=origin_city,
            state=origin_state,
            zip=origin_pincode,
            street=origin_street_addr,
            country="India",
            addressName=origin_address_name,
        ),
        Address(
            type=AddressType.DELIVERY,
            name=dest_name,
            phone=dest_phone,
            city=dest_city,
            state=dest_state,
            zip=dest_pincode,
            street=dest_street_addr,
            country="India",
            addressName=dest_address_name,
        ),
        Address(
            type=AddressType.BILLING,
            name=dest_name,
            phone=dest_phone,
            city=dest_city,
            state=dest_state,
            zip=dest_pincode,
            street=dest_street_addr,
            country="India",
            addressName=dest_address_name,
        ),
        Address(
            type=AddressType.RETURN,
            name=origin_name,
            phone=origin_phone,
            city=origin_city,
            state=origin_state,
            zip=origin_pincode,
            street=origin_street_addr,
            country="India",
            addressName=origin_address_name,
        ),
    ]
    
    # Convert numeric values to strings for Order V2 API
    shipment = Shipment(
        awbNumber=f"AW{order_id}",
        physicalWeight=str(weight_grams),
        items=[
            PackageItem(
                name=item_name,
                quantity=item_quantity,
                unitPrice=str(item_price),
                weight=str(weight_grams),
                description=item_name,
            )
        ],
    )
    
    # Map payment type string to enum
    payment_type_enum = PaymentType.PREPAID
    if payment_type.upper() == "COD":
        payment_type_enum = PaymentType.COD
    elif payment_type.upper() == "TOPAY":
        payment_type_enum = PaymentType.TOPAY
    
    payment = Payment(
        type=payment_type_enum,
        finalAmount=str(payment_amount),
        currency="INR",
        status=PaymentStatus.PENDING if payment_type_enum == PaymentType.COD else PaymentStatus.PAID,
    )
    
    # Build partner and metadata
    partner = Partner(code=partner_code)
    metadata = OrderMetadata(source="agentic-orchestrator")
    
    order = OrderRequest(
        orderId=order_id,
        partner=partner,
        metadata=metadata,
        addresses=addresses,
        parentShipment=shipment,
        payment=payment,
    )
    
    client = OrderClient()
    response = await client.create_order(order)
    
    return response.model_dump()


@tool("get_order", args_schema=GetOrderInput)
async def get_order_tool(order_id: str) -> dict:
    """
    Get details of an existing order.
    
    Use this tool when the user wants to check the status or details of an order.
    """
    client = OrderClient()
    response = await client.get_order(order_id)
    return response.model_dump()


@tool("cancel_order", args_schema=CancelOrderInput)
async def cancel_order_tool(
    order_id: str,
    reason: str,
    initiated_by: str = "CUSTOMER",
) -> dict:
    """
    Cancel an existing order.
    
    Use this tool when the user wants to cancel a shipment or order.
    """
    # Map initiator string to enum
    initiator = CancelInitiator.CUSTOMER
    if initiated_by.upper() == "MERCHANT":
        initiator = CancelInitiator.MERCHANT
    elif initiated_by.upper() == "SYSTEM":
        initiator = CancelInitiator.SYSTEM
    
    cancel_request = CancelRequest(
        reason=reason,
        initiatedBy=initiator,
    )
    
    client = OrderClient()
    response = await client.cancel_order(order_id, cancel_request)
    return response.model_dump()
