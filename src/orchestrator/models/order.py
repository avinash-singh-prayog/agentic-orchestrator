"""
Order Data Models

Order-centric data model where one Order can contain multiple Shipments.
Each Shipment contains multiple ShipmentItems.

Hierarchy:
    Order
    ├── Shipment 1
    │   ├── ShipmentItem 1.1
    │   └── ShipmentItem 1.2
    └── Shipment 2
        └── ShipmentItem 2.1
"""

import operator
from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    """Status of a shipment within an order."""
    
    PENDING = "pending"
    QUOTED = "quoted"
    APPROVED = "approved"
    BOOKED = "booked"
    IN_TRANSIT = "in_transit"
    CUSTOMS_CLEARANCE = "customs_clearance"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OrderStatus(str, Enum):
    """Overall status of an order."""
    
    CREATED = "created"
    VALIDATING = "validating"
    SERVICEABLE = "serviceable"
    NOT_SERVICEABLE = "not_serviceable"
    QUOTING = "quoting"
    QUOTED = "quoted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    BOOKING = "booking"
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ShipmentItem(BaseModel):
    """Individual item within a shipment."""
    
    item_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    description: str = Field(..., description="Item description")
    weight: float = Field(..., ge=0, description="Weight in kg")
    dimensions: str = Field(default="", description="Dimensions (LxWxH cm)")
    quantity: int = Field(default=1, ge=1, description="Number of units")
    value: float = Field(default=0.0, ge=0, description="Declared value in USD")
    is_hazardous: bool = Field(default=False, description="Hazardous material flag")
    is_fragile: bool = Field(default=False, description="Fragile item flag")


class Shipment(BaseModel):
    """
    A shipment within an order.
    
    One order can have multiple shipments (e.g., for multi-leg routes
    or when items need to be shipped from different origins).
    """
    
    shipment_id: str = Field(default_factory=lambda: str(uuid4()))
    carrier: str | None = Field(default=None, description="Selected carrier")
    tracking_number: str | None = Field(default=None, description="Carrier tracking number")
    status: ShipmentStatus = Field(default=ShipmentStatus.PENDING)
    items: list[ShipmentItem] = Field(default_factory=list)
    
    # Shipping details
    origin: str = Field(..., description="Origin address/location")
    destination: str = Field(..., description="Destination address/location")
    
    # Pricing
    quoted_price: float | None = Field(default=None, description="Quoted price in USD")
    final_price: float | None = Field(default=None, description="Final booked price in USD")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    shipped_at: datetime | None = Field(default=None)
    delivered_at: datetime | None = Field(default=None)
    
    @property
    def total_weight(self) -> float:
        """Calculate total weight of all items."""
        return sum(item.weight * item.quantity for item in self.items)
    
    @property
    def total_value(self) -> float:
        """Calculate total declared value of all items."""
        return sum(item.value * item.quantity for item in self.items)


class Order(BaseModel):
    """
    An order containing one or more shipments.
    
    This is the primary entity that flows through the orchestration workflow.
    """
    
    order_id: str = Field(default_factory=lambda: str(uuid4()))
    customer_id: str = Field(..., description="Customer identifier")
    status: OrderStatus = Field(default=OrderStatus.CREATED)
    
    # Shipments
    shipments: list[Shipment] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Error tracking
    errors: list[str] = Field(default_factory=list)
    
    @property
    def total_value(self) -> float:
        """Calculate total value across all shipments."""
        return sum(s.total_value for s in self.shipments)
    
    @property
    def total_weight(self) -> float:
        """Calculate total weight across all shipments."""
        return sum(s.total_weight for s in self.shipments)
    
    @property
    def total_quoted_price(self) -> float:
        """Calculate total quoted price across all shipments."""
        return sum(s.quoted_price or 0 for s in self.shipments)


class OrderState(dict):
    """
    LangGraph state for order processing workflow.
    
    This TypedDict-like structure is used by LangGraph to maintain
    state across workflow nodes. The messages field uses the reducer
    pattern for accumulating conversation history.
    
    Usage in LangGraph:
        class GraphState(TypedDict):
            order_id: str
            ...
            messages: Annotated[list[dict], operator.add]
    """
    
    # Order identification
    order_id: str
    customer_id: str
    
    # Locations
    origin: str
    destination: str
    
    # Shipment data
    shipments: list[dict[str, Any]]
    
    # Workflow state
    messages: Annotated[list[dict[str, Any]], operator.add]
    is_serviceable: bool | None
    quotes: list[dict[str, Any]]
    selected_quote: dict[str, Any] | None
    approval_status: str | None  # PENDING, APPROVED, REJECTED
    booking_confirmation: str | None
    
    # Error handling
    errors: list[str]


# Type alias for LangGraph state
from typing import TypedDict


class GraphState(TypedDict):
    """LangGraph state type for the orchestration workflow."""
    
    order_id: str
    customer_id: str
    origin: str
    destination: str
    shipments: list[dict[str, Any]]
    messages: Annotated[list[dict[str, Any]], operator.add]
    is_serviceable: bool | None
    quotes: list[dict[str, Any]]
    selected_quote: dict[str, Any] | None
    approval_status: str | None
    booking_confirmation: str | None
    errors: list[str]
    next_node: str
    full_response: str
