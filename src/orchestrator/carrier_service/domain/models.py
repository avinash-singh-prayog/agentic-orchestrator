"""
Domain Models for Carrier Service.

Unified Pydantic data models so the agent speaks one language,
regardless of the carrier being used.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CarrierType(str, Enum):
    """Enumeration of supported carrier types."""

    DHL = "dhl"
    INDIA_POST = "india_post"
    MOCK = "mock"


class ShipmentRequest(BaseModel):
    """Request model for creating a shipment."""

    origin_pincode: str = Field(..., description="Origin postal/pin code")
    dest_pincode: str = Field(..., description="Destination postal/pin code")
    weight_kg: float = Field(..., gt=0, description="Package weight in kilograms")
    description: str = Field(default="General Goods", description="Contents description")
    length_cm: Optional[float] = Field(default=None, description="Package length in cm")
    width_cm: Optional[float] = Field(default=None, description="Package width in cm")
    height_cm: Optional[float] = Field(default=None, description="Package height in cm")


class RateQuote(BaseModel):
    """Rate quote from a carrier."""

    carrier: CarrierType
    service_name: str = Field(..., description="Name of the service tier")
    service_code: str = Field(..., description="Internal service code for booking")
    price: float = Field(..., ge=0, description="Total price for shipment")
    currency: str = Field(default="USD", description="Currency code")
    estimated_delivery_days: int = Field(..., ge=0, description="Estimated delivery time")


class LabelResponse(BaseModel):
    """Response after successfully creating a shipment."""

    tracking_number: str = Field(..., description="Carrier tracking number")
    label_url: str = Field(..., description="URL to download shipping label")
    carrier: CarrierType


class ServiceabilityResult(BaseModel):
    """Result of serviceability check."""

    origin: str
    destination: str
    is_serviceable: bool
    carrier: CarrierType
    message: Optional[str] = None
