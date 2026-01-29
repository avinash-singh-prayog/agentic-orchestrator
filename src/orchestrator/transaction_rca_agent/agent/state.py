"""
Transaction RCA Agent State.

LangGraph state management for the transaction RCA agent workflow.
"""

from typing import Optional

from langgraph.graph import MessagesState

from domain.models import TransactionContext, RCAAnalysis, HumanIntervention


class TransactionRCAAgentState(MessagesState):
    """
    State for the Transaction RCA agent workflow.

    Extends MessagesState to include RCA-specific state fields.
    """

    # Parsed transaction context from input
    transaction_context: Optional[TransactionContext] = None

    # RCA analysis result
    rca_analysis: Optional[RCAAnalysis] = None

    # Human intervention prompt
    human_intervention: Optional[HumanIntervention] = None

    # Error message if any step fails
    error: Optional[str] = None
