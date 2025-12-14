"""
Aramex Serviceability API Models.

Pydantic models matching Aramex IsAddressServiced API structure.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AramexClientInfo(BaseModel):
    """Aramex API client credentials."""

    UserName: str
    Password: str
    Version: str = "v1.0"
    AccountNumber: str
    AccountPin: str
    AccountEntity: str
    AccountCountryCode: str
    Source: int = 24


class AramexAddress(BaseModel):
    """Aramex address for serviceability check."""

    Line1: str = ""
    Line2: str = ""
    Line3: str = ""
    City: str = ""
    StateOrProvinceCode: str = ""
    PostCode: str
    CountryCode: str
    Longitude: float = 0
    Latitude: float = 0
    BuildingNumber: Optional[str] = None
    BuildingName: Optional[str] = None
    Floor: Optional[str] = None
    Apartment: Optional[str] = None
    POBox: Optional[str] = None
    Description: Optional[str] = None


class AramexServiceDetails(BaseModel):
    """Aramex service configuration."""

    ProductGroup: str = "EXP"  # Express shipments
    ProductType: str = "PPX"  # Priority Parcel Express
    ServiceMode: int = 1  # 1=Pickup, 2=Delivery, 3=Both


class AramexTransaction(BaseModel):
    """Aramex transaction references (unused)."""

    Reference1: str = ""
    Reference2: str = ""
    Reference3: str = ""
    Reference4: str = ""
    Reference5: str = ""


class AramexServiceabilityRequest(BaseModel):
    """Full Aramex serviceability API request."""

    ClientInfo: AramexClientInfo
    Address: AramexAddress
    ServiceDetails: AramexServiceDetails = Field(default_factory=AramexServiceDetails)
    Transaction: AramexTransaction = Field(default_factory=AramexTransaction)


class AramexServiceabilityResponse(BaseModel):
    """Parsed Aramex serviceability response."""

    has_errors: bool = False
    is_serviced: bool = False
