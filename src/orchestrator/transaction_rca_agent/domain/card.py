"""
Transaction RCA Agent Identity Card and Skills.

Defines the AgentCard per the A2A protocol specification.
"""

from a2a.types import AgentCard, AgentSkill, AgentCapabilities


TransactionRCAAgentCard = AgentCard(
    name="Transaction RCA Agent",
    id="transaction-rca-agent",  # This becomes the routable topic
    description="AI agent for root cause analysis of unprocessed transactions. Performs stateless RCA analysis with evidence-backed reasoning.",
    url="",  # Empty for SLIM transport
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="analyze_transaction",
            name="Analyze Transaction RCA",
            description="Perform root cause analysis on an unprocessed transaction. Classifies the issue into one of: Sync Issues, Configuration Issues, Routing Issues, Dependency Failures, Merchant Data Issues, Compliance / Risk Holds, or Unknown / System Defect. Provides evidence-backed reasoning with confidence scores.",
            tags=["rca", "transaction", "analysis", "fintech", "root-cause"],
            examples=[
                "Analyze transaction TXN12345 for root cause",
                "What is the root cause of unprocessed transaction ABC123?",
                "Perform RCA on transaction that failed at settlement",
            ],
        ),
    ],
    supportsAuthenticatedExtendedCard=False,
)
