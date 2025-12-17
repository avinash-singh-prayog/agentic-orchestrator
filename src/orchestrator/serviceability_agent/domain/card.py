"""
Serviceability Agent Identity Card and Skills.

Defines the AgentCard and AgentSkills per the A2A protocol specification.
"""

from a2a.types import AgentCard, AgentSkill, AgentCapabilities

# Define the Agent Card following the guide's structure
# Define the Agent Card following the guide's structure
ServiceabilityAgentCard = AgentCard(
    name='Serviceability Agent',
    id='serviceability-agent',  # This becomes the routable topic
    description='AI agent responsible for serviceability checks and rate quotes. Not for shipment booking.',
    url='',  # Empty for SLIM transport
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="check_serviceability",
            name="Check Serviceability and Rates",
            description="Check if shipping is available between two locations and retrieve available partners and shipping rates.",
            tags=["logistics", "shipping", "serviceability", "rates"],
            examples=[
                "Check if we can ship from 400001 to 110001",
                "Is shipping available from Mumbai to Delhi?",
                "What are the shipping rates from Bangalore to Chennai?",
            ],
        ),
    ],
    supportsAuthenticatedExtendedCard=False,
)
