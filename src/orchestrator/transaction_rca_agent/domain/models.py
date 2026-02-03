"""
Domain Models for Transaction RCA Agent.

Pydantic models for transaction context input and RCA analysis output.
"""

from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class TransactionCheckpoint(BaseModel):
    """System checkpoint status - flexible format accepting any fields."""

    model_config = ConfigDict(extra="allow")  # Allow arbitrary fields

    checkpoint_name: Optional[str] = Field(
        None, description="Checkpoint name: ingestion, authorization, routing, ledger, settlement_file_generated, bank_acknowledged, credited"
    )
    status: Optional[str] = Field(None, description="Status: success, pending, failed")
    timestamp: Optional[str] = Field(None, description="Timestamp of checkpoint")
    details: Optional[dict] = Field(None, description="Additional checkpoint details")


class TransactionContext(BaseModel):
    """Input transaction context for RCA analysis - flexible format accepting any transaction structure."""

    model_config = ConfigDict(
        extra="allow",  # Allow arbitrary fields
        validate_assignment=False,  # Don't validate on assignment
        arbitrary_types_allowed=True,  # Allow arbitrary types
    )

    transaction_id: Optional[Any] = Field(None, description="Unique transaction identifier")
    checkpoints: Optional[Any] = Field(
        None, description="System checkpoints (can be dict, list, or any format)"
    )
    merchant_config: Optional[Any] = Field(
        None, description="Merchant configuration: TID, MDR, routing config"
    )
    merchant_data: Optional[Any] = Field(
        None, description="Merchant master data: Account, IFSC, bank details"
    )
    external_signals: Optional[Any] = Field(
        None, description="External dependency signals: Bank health, rejections"
    )
    risk_indicators: Optional[Any] = Field(
        None, description="Risk and compliance indicators"
    )
    observational_notes: Optional[Any] = Field(
        None, description="Optional observational notes (can be string, list, or any format)"
    )
    
    @model_validator(mode='before')
    @classmethod
    def normalize_all_fields(cls, data: Any) -> Dict[str, Any]:
        """Root validator that normalizes ALL fields before any validation happens."""
        if not isinstance(data, dict):
            # If not a dict, wrap it
            return {"data": data}
        
        normalized = dict(data)
        
        # Normalize checkpoints - handle dict, list, or any format
        if 'checkpoints' in normalized:
            checkpoints = normalized['checkpoints']
            if checkpoints is not None:
                if isinstance(checkpoints, list):
                    # Already a list, keep as-is
                    pass
                elif isinstance(checkpoints, dict):
                    # Convert dict to list format
                    checkpoints_list = []
                    for checkpoint_name, checkpoint_data in checkpoints.items():
                        if isinstance(checkpoint_data, dict):
                            checkpoint_obj = {
                                "checkpoint_name": checkpoint_name,
                                "status": checkpoint_data.get("status", "UNKNOWN"),
                                "timestamp": checkpoint_data.get("timestamp"),
                                "details": checkpoint_data.get("details", {})
                            }
                            checkpoints_list.append(checkpoint_obj)
                        else:
                            checkpoint_obj = {
                                "checkpoint_name": checkpoint_name,
                                "status": str(checkpoint_data) if checkpoint_data else "UNKNOWN",
                                "timestamp": None,
                                "details": {}
                            }
                            checkpoints_list.append(checkpoint_obj)
                    normalized['checkpoints'] = checkpoints_list
                else:
                    # Any other type, wrap it
                    normalized['checkpoints'] = [{"data": checkpoints}]
        
        # Normalize observational_notes - handle string, list, or any format
        if 'observational_notes' in normalized:
            notes = normalized['observational_notes']
            if notes is not None:
                if isinstance(notes, str):
                    # Already a string, keep as-is
                    pass
                elif isinstance(notes, list):
                    # Convert list to string
                    normalized['observational_notes'] = "; ".join(str(item) for item in notes)
                else:
                    # Any other type, convert to string
                    normalized['observational_notes'] = str(notes)
        
        return normalized


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
