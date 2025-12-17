"""
Booking Agent Identity Card and Skills.

Defines the AgentCard per the A2A protocol specification.
"""

from a2a.types import AgentCard, AgentSkill, AgentCapabilities


BookingAgentCard = AgentCard(
    name='Booking Agent',
    id='booking-agent',  # This becomes the routable SLIM topic
    description='AI agent for shipment booking and order functions (create, get, cancel) via Order V2 APIs.',
    url='',  # Empty for SLIM transport
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="create_order",
            name="Create Order",
            description="Create a new shipping order with pickup and delivery addresses.",
            tags=["logistics", "order", "booking", "shipping"],
            examples=[
                "Create an order from Mumbai to Delhi for 2kg package",
                "Book a shipment from 400001 to 110001 with COD payment",
                "I need to ship 5kg from Bangalore to Chennai",
            ],
        ),
        AgentSkill(
            id="get_order",
            name="Get Order Status",
            description="Retrieve the status and details of an existing order.",
            tags=["logistics", "order", "tracking", "status"],
            examples=[
                "What is the status of order ORD12345?",
                "Get details for order ABC123",
                "Check my order status",
            ],
        ),
        AgentSkill(
            id="cancel_order",
            name="Cancel Order",
            description="Cancel an existing order and process refund if applicable.",
            tags=["logistics", "order", "cancel", "refund"],
            examples=[
                "Cancel order ORD12345",
                "I want to cancel my shipment",
                "Please cancel order ABC123 - customer changed their mind",
            ],
        ),
    ],
    supportsAuthenticatedExtendedCard=False,
)
