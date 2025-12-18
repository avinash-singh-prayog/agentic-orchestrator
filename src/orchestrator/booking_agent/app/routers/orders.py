"""
Orders API router for the Booking Agent.

Provides REST endpoints to create, get, list, and cancel orders.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field

from ...services.order.client import OrderClient
from ...domain.models import (
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
from ...domain.exceptions import OrderAPIError, OrderNotFoundError

logger = logging.getLogger("booking_agent.orders")

router = APIRouter(tags=["Orders"])


# =============================================================================
# Request/Response Models
# =============================================================================

class AddressInput(BaseModel):
    """Address input for order creation."""
    name: str = Field(..., description="Contact name")
    phone: str = Field(..., description="Phone number")
    street: str = Field(default="", description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State/Province")
    zip: str = Field(..., description="Postal/ZIP code")
    country: str = Field(default="India", description="Country")


class PackageInput(BaseModel):
    """Package input for order creation."""
    name: str = Field(default="General Goods", description="Item name")
    quantity: int = Field(default=1, description="Quantity")
    unit_price: float = Field(default=100.0, description="Unit price")
    weight_grams: float = Field(..., description="Weight in grams")


class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""
    order_id: str = Field(..., description="Unique order identifier")
    partner_code: str = Field(..., description="Partner/carrier code (e.g. smile_hubops)")
    origin: AddressInput = Field(..., description="Pickup/origin address")
    destination: AddressInput = Field(..., description="Delivery/destination address")
    package: PackageInput = Field(..., description="Package details")
    payment_type: str = Field(default="PREPAID", description="PREPAID, COD, or TOPAY")
    payment_amount: float = Field(..., description="Total payment amount")
    service_type: str = Field(default="standard", description="Service type")
    delivery_mode: str = Field(default="SURFACE", description="Delivery mode: SURFACE, EXPRESS")


class CancelOrderRequest(BaseModel):
    """Request model for canceling an order."""
    reason: str = Field(..., description="Cancellation reason")
    initiated_by: str = Field(default="CUSTOMER", description="CUSTOMER, MERCHANT, or SYSTEM")


class OrderAPIResponse(BaseModel):
    """Generic API response."""
    success: bool
    message: str
    data: Optional[dict] = None
    meta: Optional[dict] = None


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/orders", response_model=OrderAPIResponse)
async def create_order(
    request: CreateOrderRequest,
    x_tenant_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> OrderAPIResponse:
    """
    Create a new shipping order.

    Example:
        POST /booking-agent/v1/orders
        {
            "order_id": "ORD-001",
            "partner_code": "smile_hubops",
            "origin": {"name": "Sender", "phone": "9876543210", "city": "Mumbai", "state": "Maharashtra", "zip": "400001"},
            "destination": {"name": "Receiver", "phone": "9876543211", "city": "Delhi", "state": "Delhi", "zip": "110001"},
            "package": {"weight_grams": 2000},
            "payment_type": "PREPAID",
            "payment_amount": 500
        }
    """
    logger.info(f"Creating order: {request.order_id} with partner: {request.partner_code}")

    # Build origin address
    origin_street = request.origin.street or f"{request.origin.city} Main Road"
    origin_address_name = f"{origin_street}, {request.origin.city}, {request.origin.zip}, {request.origin.state}, {request.origin.country}"
    
    # Build destination address
    dest_street = request.destination.street or f"{request.destination.city} Main Road"
    dest_address_name = f"{dest_street}, {request.destination.city}, {request.destination.zip}, {request.destination.state}, {request.destination.country}"

    # Build all 4 address types
    addresses = [
        Address(
            type=AddressType.PICKUP,
            name=request.origin.name,
            phone=request.origin.phone,
            street=origin_street,
            city=request.origin.city,
            state=request.origin.state,
            zip=request.origin.zip,
            country=request.origin.country,
            addressName=origin_address_name,
        ),
        Address(
            type=AddressType.DELIVERY,
            name=request.destination.name,
            phone=request.destination.phone,
            street=dest_street,
            city=request.destination.city,
            state=request.destination.state,
            zip=request.destination.zip,
            country=request.destination.country,
            addressName=dest_address_name,
        ),
        Address(
            type=AddressType.BILLING,
            name=request.destination.name,
            phone=request.destination.phone,
            street=dest_street,
            city=request.destination.city,
            state=request.destination.state,
            zip=request.destination.zip,
            country=request.destination.country,
            addressName=dest_address_name,
        ),
        Address(
            type=AddressType.RETURN,
            name=request.origin.name,
            phone=request.origin.phone,
            street=origin_street,
            city=request.origin.city,
            state=request.origin.state,
            zip=request.origin.zip,
            country=request.origin.country,
            addressName=origin_address_name,
        ),
    ]

    shipment = Shipment(
        awbNumber=f"AW{request.order_id}",
        physicalWeight=str(request.package.weight_grams),
        items=[
            PackageItem(
                name=request.package.name,
                quantity=request.package.quantity,
                unitPrice=str(request.package.unit_price),
                weight=str(request.package.weight_grams),
                description=request.package.name,
            )
        ],
    )

    # Map payment type
    payment_type_enum = PaymentType.PREPAID
    if request.payment_type.upper() == "COD":
        payment_type_enum = PaymentType.COD
    elif request.payment_type.upper() == "TOPAY":
        payment_type_enum = PaymentType.TOPAY

    payment = Payment(
        type=payment_type_enum,
        finalAmount=str(request.payment_amount),
        currency="INR",
        status=PaymentStatus.PENDING if payment_type_enum == PaymentType.COD else PaymentStatus.PAID,
    )

    # Build partner and metadata
    partner = Partner(code=request.partner_code)
    metadata = OrderMetadata(
        source="agentic-orchestrator",
        createdBy=x_user_id or "",
    )

    order = OrderRequest(
        orderId=request.order_id,
        partner=partner,
        metadata=metadata,
        addresses=addresses,
        parentShipment=shipment,
        payment=payment,
        serviceType=request.service_type,
        deliveryMode=request.delivery_mode,
    )

    try:
        client = OrderClient(tenant_id=x_tenant_id, user_id=x_user_id)
        response = await client.create_order(order)
        return OrderAPIResponse(
            success=response.success,
            message=response.message,
            data=response.data,
        )
    except OrderAPIError as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.get("/orders/{order_id}", response_model=OrderAPIResponse)
async def get_order(
    order_id: str,
    x_tenant_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> OrderAPIResponse:
    """
    Get order details by ID.

    Example:
        GET /booking/v1/orders/ORD-001
    """
    logger.info(f"Fetching order: {order_id}")

    try:
        client = OrderClient(tenant_id=x_tenant_id, user_id=x_user_id)
        response = await client.get_order(order_id)
        return OrderAPIResponse(
            success=response.success,
            message=response.message,
            data=response.data,
        )
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    except OrderAPIError as e:
        logger.error(f"Get order failed: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.get("/orders", response_model=OrderAPIResponse)
async def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    order_status: Optional[str] = Query(None, description="Filter by status"),
    reference_id: Optional[str] = Query(None, description="Filter by reference ID"),
    x_tenant_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> OrderAPIResponse:
    """
    List orders with pagination.

    Example:
        GET /booking/v1/orders?page=1&limit=10&order_status=PENDING
    """
    logger.info(f"Listing orders: page={page}, limit={limit}")

    try:
        client = OrderClient(tenant_id=x_tenant_id, user_id=x_user_id)
        response = await client.get_orders(
            page=page,
            limit=limit,
            order_status=order_status,
            reference_id=reference_id,
        )
        return OrderAPIResponse(
            success=response.success,
            message=response.message,
            data=response.data,
            meta=response.meta,
        )
    except OrderAPIError as e:
        logger.error(f"List orders failed: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.post("/orders/{order_id}/cancel", response_model=OrderAPIResponse)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    x_tenant_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> OrderAPIResponse:
    """
    Cancel an existing order.

    Example:
        POST /booking/v1/orders/ORD-001/cancel
        {
            "reason": "Customer changed mind",
            "initiated_by": "CUSTOMER"
        }
    """
    logger.info(f"Cancelling order: {order_id}")

    # Map initiator
    initiator = CancelInitiator.CUSTOMER
    if request.initiated_by.upper() == "MERCHANT":
        initiator = CancelInitiator.MERCHANT
    elif request.initiated_by.upper() == "SYSTEM":
        initiator = CancelInitiator.SYSTEM

    cancel_req = CancelRequest(
        reason=request.reason,
        initiatedBy=initiator,
    )

    try:
        client = OrderClient(tenant_id=x_tenant_id, user_id=x_user_id)
        response = await client.cancel_order(order_id, cancel_req)
        return OrderAPIResponse(
            success=response.success,
            message=response.message,
            data=response.data,
        )
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    except OrderAPIError as e:
        logger.error(f"Cancel order failed: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
