"""
Serviceability Agent Identity Card and Skills.

Defines the AgentCard and AgentSkills per the A2A protocol specification.
"""

from a2a.types import AgentCard, AgentSkill, AgentCapabilities

# Define the Agent Card following the guide's structure
ServiceabilityAgentCard = AgentCard(
    name='Serviceability Agent',
    id='serviceability-agent',  # This becomes the routable topic
    description='AI agent responsible for serviceability checks, rate quotes, and shipment booking.',
    url='',  # Empty for SLIM transport
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="check_serviceability",
            name="Check Serviceability",
            description="Check if shipping is available between two locations and retrieve available partners.",
            tags=["logistics", "shipping", "serviceability"],
            examples=[
                "Check if we can ship from 400001 to 110001",
                "Is shipping available from Mumbai to Delhi?",
            ],
        ),
        AgentSkill(
            id="get_rates",
            name="Get Shipping Rates",
            description="Get shipping rates for a route with specified weight.",
            tags=["logistics", "rates", "pricing"],
            examples=[
                "Get rates for 5kg from Mumbai to Delhi",
                "What are the shipping costs from 400001 to 110001?",
            ],
        ),
    ],
    supportsAuthenticatedExtendedCard=False,
)
