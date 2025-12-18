"""
Domain Models for Serviceability Agent.

Unified Pydantic data models so the agent speaks one language,
regardless of the carrier being used.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PartnerCode(str, Enum):
    """Enumeration of supported partner codes."""

    ARAMEX = "aramex"
    DHL = "dhl"
    INDIA_POST = "india_post"
    MOCK = "mock"


# =============================================================================
# Standardized Serviceability Request Models
# =============================================================================


class Location(BaseModel):
    """Location with postal code and country."""

    postal_code: str = Field(..., description="Postal/PIN code")
    country_code: str = Field(default="IN", description="ISO 2-letter country code")


class Weight(BaseModel):
    """Weight specification."""

    value: float = Field(..., gt=0, description="Weight value")
    unit: str = Field(default="kg", description="Weight unit (kg, lb)")


class Dimensions(BaseModel):
    """Package dimensions."""

    length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    unit: str = Field(default="cm", description="Dimension unit (cm, in)")


class Package(BaseModel):
    """Package with weight and optional dimensions."""

    weight: Weight
    dimensions: Optional[Dimensions] = None


class PartnerFilter(BaseModel):
    """Filter for specific partners."""

    id: Optional[str] = Field(default=None, description="Carrier ID")
    code: str = Field(..., description="Carrier code")


class ServiceabilityMetadata(BaseModel):
    """Metadata for serviceability request."""

    currency: str = Field(default="INR")
    service_type: str = Field(default="express")


class ServiceabilityRequest(BaseModel):
    """Standardized serviceability check request."""

    source_location: Location
    destination_location: Location
    packages: List[Package] = Field(default_factory=list)
    partners: List[PartnerFilter] = Field(
        default_factory=list, description="Empty = check all partners"
    )
    metadata: Optional[ServiceabilityMetadata] = None


# =============================================================================
# Legacy/Existing Models (Updated to use CarrierCode)
# =============================================================================


class ShipmentRequest(BaseModel):
    """Request model for creating a shipment."""

    origin_pincode: str = Field(..., description="Origin postal/pin code")
    dest_pincode: str = Field(..., description="Destination postal/pin code")
    weight_kg: float = Field(..., gt=0, description="Package weight in kilograms")
    description: str = Field(default="General Goods", description="Contents description")
    origin_country: str = Field(default="IN", description="Origin country code")
    dest_country: str = Field(default="IN", description="Destination country code")
    length_cm: Optional[float] = Field(default=None, description="Package length in cm")
    width_cm: Optional[float] = Field(default=None, description="Package width in cm")
    height_cm: Optional[float] = Field(default=None, description="Package height in cm")


class RateQuote(BaseModel):
    """Rate quote from a carrier."""

    carrier: PartnerCode
    service_name: str = Field(..., description="Name of the service tier")
    service_code: str = Field(..., description="Internal service code for booking")
    price: float = Field(..., ge=0, description="Total price for shipment")
    currency: str = Field(default="USD", description="Currency code")
    estimated_delivery_days: int = Field(..., ge=0, description="Estimated delivery time")


class LabelResponse(BaseModel):
    """Response after successfully creating a shipment."""

    tracking_number: str = Field(..., description="Carrier tracking number")
    label_url: str = Field(..., description="URL to download shipping label")
    carrier: PartnerCode


class ServiceProductTypes(BaseModel):
    """Product types supported by the service."""

    commercial: bool = True
    document: bool = True
    non_document: bool = True


class ServiceDeliveryModes(BaseModel):
    """Delivery modes supported by the service."""

    express: bool = False
    standard: bool = True


# =============================================================================
# Serviceability Response Models (Matching External API)
# =============================================================================


class Money(BaseModel):
    """Monetary value."""

    currency: str = Field(..., description="Currency code (e.g. INR, USD)")
    amount: float = Field(..., description="Amount value")
    type: str = Field(default="standard", description="Type of charge")


class Rate(BaseModel):
    """Rate details for a service."""

    rate_id: str
    price: Money
    description: Optional[str] = None


class PartnerService(BaseModel):
    """A service offered by a carrier/partner."""

    service_code: str
    service_name: str
    tat_days: int = Field(default=0, description="Transit time in days")
    is_cod: bool = False
    pickup: bool = True
    delivery: bool = True
    insurance: bool = True
    product_types: ServiceProductTypes = Field(default_factory=ServiceProductTypes)
    delivery_modes: ServiceDeliveryModes = Field(default_factory=ServiceDeliveryModes)
    rate: Optional[Rate] = None  # Added rate field


class Partner(BaseModel):
    """Partner (Carrier) details in serviceability response."""

    partner_id: str
    partner_code: str
    partner_name: str
    rating: float = 0
    source: str = "real_time"
    is_serviceable: bool
    services: List[PartnerService] = Field(default_factory=list)
    response_time_ms: int = 0
    metadata: Optional[dict] = None


class ServiceabilityResponse(BaseModel):
    """Top-level serviceability API response."""

    success: bool
    message: str
    partners: List[Partner] = Field(default_factory=list)
    metadata: Optional[dict] = None


# Retrofit ServiceabilityResult to be an alias or compat layer if needed,
# or we can remove it if we fully switch. For now, keeping a compat version
# is safer for untracked usages, but since we deleted the main consumer,
# let's deprecate checking 'ServiceabilityResult' in favor of 'Partner'.
# We can keep 'CarrierCode' as it might be useful.


