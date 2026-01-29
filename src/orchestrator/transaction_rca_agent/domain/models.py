"""
Domain Models for Transaction RCA Agent.

Pydantic models for transaction context input and RCA analysis output.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TransactionCheckpoint(BaseModel):
    """System checkpoint status."""

    checkpoint_name: str = Field(
        ..., description="Checkpoint name: ingestion, authorization, routing, ledger, settlement_file_generated, bank_acknowledged, credited"
    )
    status: str = Field(..., description="Status: success, pending, failed")
    timestamp: Optional[str] = Field(None, description="Timestamp of checkpoint")
    details: Optional[dict] = Field(None, description="Additional checkpoint details")


class TransactionContext(BaseModel):
    """Input transaction context for RCA analysis."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    checkpoints: List[TransactionCheckpoint] = Field(
        ..., description="List of system checkpoints with their status"
    )
    merchant_config: Optional[dict] = Field(
        None, description="Merchant configuration: TID, MDR, routing config"
    )
    merchant_data: Optional[dict] = Field(
        None, description="Merchant master data: Account, IFSC, bank details"
    )
    external_signals: Optional[dict] = Field(
        None, description="External dependency signals: Bank health, rejections"
    )
    risk_indicators: Optional[dict] = Field(
        None, description="Risk and compliance indicators"
    )
    observational_notes: Optional[str] = Field(
        None, description="Optional observational notes"
    )


class RCAAnalysis(BaseModel):
    """RCA analysis result."""

    rca_category: str = Field(
        ...,
        description="One of: Sync Issues, Configuration Issues, Routing Issues, Dependency Failures, Merchant Data Issues, Compliance / Risk Holds, Unknown / System Defect",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    last_successful_checkpoint: str = Field(
        ..., description="Name of the last successful checkpoint"
    )
    transaction_narrative: str = Field(
        ..., description="Concise journey summary of the transaction"
    )
    key_anomalies: List[str] = Field(
        ..., description="List of abnormal or missing observations"
    )
    contradictions_observed: List[str] = Field(
        ..., description="List of conflicting signals, if any"
    )
    evidence: List[str] = Field(
        ..., description="List of explicit evidence taken directly from input"
    )
    alternative_causes_considered: List[str] = Field(
        ..., description="List of other plausible categories evaluated"
    )
    final_reasoning: str = Field(
        ..., description="Explanation of why this RCA category fits best"
    )


class HumanIntervention(BaseModel):
    """Human-in-the-loop prompt."""

    action_required: bool = Field(
        ..., description="Whether human intervention is required"
    )
    prompt: str = Field(
        ..., description="Prompt for human decision on ticket creation"
    )


class RCAResponse(BaseModel):
    """Complete RCA response matching the output contract."""

    rca_analysis: RCAAnalysis = Field(..., description="RCA analysis result")
    human_intervention: HumanIntervention = Field(
        ..., description="Human intervention prompt"
    )
