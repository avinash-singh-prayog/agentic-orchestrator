"""
Domain Models for Booking Agent.

Pydantic models representing Order V2 API structures.
"""

from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class AddressType(str, Enum):
    """Address type enumeration."""
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"


class ParcelCategory(str, Enum):
    """Parcel category enumeration."""
    COURIER = "COURIER"
    INTERNATIONAL = "INTERNATIONAL"
    ECOMM = "ECOMM"
    CARGO = "CARGO"


class OrderType(str, Enum):
    """Order type enumeration."""
    FORWARD = "FORWARD"
    RETURN = "RETURN"


class PaymentType(str, Enum):
    """Payment type enumeration."""
    PREPAID = "PREPAID"
    COD = "COD"
    TOPAY = "TOPAY"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    DRAFT = "DRAFT"
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class CancelInitiator(str, Enum):
    """Who initiated the cancellation."""
    CUSTOMER = "CUSTOMER"
    MERCHANT = "MERCHANT"
    SYSTEM = "SYSTEM"


class RefundMethod(str, Enum):
    """Refund method enumeration."""
    ORIGINAL_SOURCE = "ORIGINAL_SOURCE"
    WALLET = "WALLET"
    BANK_TRANSFER = "BANK_TRANSFER"


# =============================================================================
# Address Models
# =============================================================================


class Address(BaseModel):
    """Address for pickup or delivery."""
    type: AddressType = Field(..., description="Address type: PICKUP or DELIVERY")
    name: str = Field(..., description="Contact name")
    phone: str = Field(..., description="Contact phone number")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State/Province")
    country: str = Field(default="India", description="Country name")
    zip: str = Field(..., description="Postal/ZIP code")
    street: str = Field(..., description="Street address")


# =============================================================================
# Package Models
# =============================================================================


class Dimensions(BaseModel):
    """Package dimensions."""
    length: float = Field(..., gt=0, description="Length in cm")
    width: float = Field(..., gt=0, description="Width in cm")
    height: float = Field(..., gt=0, description="Height in cm")


class PackageItem(BaseModel):
    """Individual item in a shipment."""
    name: str = Field(..., description="Item name")
    quantity: int = Field(..., ge=1, description="Item quantity")
    unitPrice: float = Field(..., ge=0, description="Price per unit")
    weight: float = Field(..., ge=0, description="Item weight in grams")
    sku: Optional[str] = Field(default=None, description="Stock Keeping Unit")
    hsnCode: Optional[str] = Field(default=None, description="HSN code for tax")


class Packaging(BaseModel):
    """Packaging details."""
    type: str = Field(default="BOX", description="Packaging type")
    fragileHandling: bool = Field(default=False, description="Requires fragile handling")


class Shipment(BaseModel):
    """Shipment details (parent or child)."""
    awbNumber: str = Field(..., description="Air Waybill number")
    physicalWeight: float = Field(..., gt=0, description="Physical weight in grams")
    volumetricWeight: Optional[float] = Field(default=None, description="Volumetric weight in grams")
    dimensions: Optional[Dimensions] = None
    items: List[PackageItem] = Field(default_factory=list, description="Items in shipment")
    packaging: Optional[Packaging] = None
    note: Optional[str] = Field(default=None, description="Special instructions")


# =============================================================================
# Payment Models
# =============================================================================


class Payment(BaseModel):
    """Payment details."""
    type: PaymentType = Field(..., description="Payment type")
    finalAmount: float = Field(..., ge=0, description="Total amount")
    currency: str = Field(default="INR", description="Currency code")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Payment status")


class RefundInstructions(BaseModel):
    """Refund instructions for cancellation."""
    refundMethod: RefundMethod = Field(default=RefundMethod.ORIGINAL_SOURCE)
    refundAmount: float = Field(..., ge=0)


# =============================================================================
# Order Request Models
# =============================================================================


class OrderRequest(BaseModel):
    """Request model for creating an order."""
    orderId: str = Field(..., description="Unique order identifier")
    referenceId: Optional[str] = Field(default=None, description="External reference ID")
    parcelCategory: ParcelCategory = Field(default=ParcelCategory.COURIER)
    orderDate: Optional[datetime] = Field(default=None, description="Order creation date")
    expectedDeliveryDate: Optional[datetime] = Field(default=None, description="Expected delivery date")
    orderType: OrderType = Field(default=OrderType.FORWARD)
    autoManifest: bool = Field(default=True, description="Auto-manifest the order")
    addresses: List[Address] = Field(..., min_length=2, description="Pickup and delivery addresses")
    parentShipment: Shipment = Field(..., description="Main shipment details")
    childShipments: List[Shipment] = Field(default_factory=list, description="Child shipments")
    payment: Payment = Field(..., description="Payment details")


class CancelRequest(BaseModel):
    """Request model for cancelling an order."""
    reason: str = Field(..., description="Cancellation reason")
    initiatedBy: CancelInitiator = Field(default=CancelInitiator.CUSTOMER)
    refundInstructions: Optional[RefundInstructions] = None


class BulkOrderRequest(BaseModel):
    """Request for creating multiple orders."""
    orders: List[OrderRequest] = Field(..., min_length=1)


class BulkCancelRequest(BaseModel):
    """Request for cancelling multiple orders."""
    orderIds: Optional[List[str]] = None
    reason: Optional[str] = None
    orders: Optional[List[dict]] = None


# =============================================================================
# Order Response Models
# =============================================================================


class OrderResponse(BaseModel):
    """Response model from Order API."""
    success: bool = Field(..., description="Operation success status")
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Response message")
    data: Optional[dict] = Field(default=None, description="Order data")
    meta: Optional[dict] = Field(default=None, description="Pagination metadata")


class BulkOrderResponse(BaseModel):
    """Response from bulk order creation."""
    success: bool
    statusCode: int
    message: str
    data: Optional[dict] = None


# =============================================================================
# Agent-Specific Models (for LLM extraction)
# =============================================================================


class ExtractedOrderIntent(BaseModel):
    """Order intent extracted from user message."""
    action: str = Field(..., description="Action: create, get, cancel, update")
    order_id: Optional[str] = Field(default=None, description="Order ID if referencing existing order")
    origin_pincode: Optional[str] = Field(default=None, description="Origin postal code")
    dest_pincode: Optional[str] = Field(default=None, description="Destination postal code")
    weight_kg: Optional[float] = Field(default=None, description="Weight in kg")
    payment_type: Optional[str] = Field(default=None, description="PREPAID, COD, or TOPAY")
    item_description: Optional[str] = Field(default=None, description="Item description")
    cancel_reason: Optional[str] = Field(default=None, description="Reason for cancellation")
