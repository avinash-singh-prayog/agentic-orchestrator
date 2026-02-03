"""
RCA Analysis API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from database.base import get_db
from database.models import RCACategory
from services.database_service import RCAAnalysisService, TransactionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rca", tags=["RCA Analysis"])


# ============================================================================
# Request/Response Models
# ============================================================================

class RCAAnalysisCreateRequest(BaseModel):
    """Request to create an RCA analysis."""
    transaction_id: str = Field(..., description="Transaction ID (UUID or transaction_id string)")
    rca_category: str = Field(..., description="RCA category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    last_successful_checkpoint: str
    transaction_narrative: str
    key_anomalies: List[str]
    contradictions_observed: List[str]
    evidence: List[str]
    alternative_causes_considered: List[str]
    final_reasoning: str
    action_required: bool = False
    intervention_prompt: Optional[str] = None


class RCAAnalysisResponse(BaseModel):
    """RCA analysis response model."""
    id: str
    transaction_id: str
    rca_category: str
    confidence: float
    last_successful_checkpoint: str
    transaction_narrative: str
    key_anomalies: List[str]
    contradictions_observed: List[str]
    evidence: List[str]
    alternative_causes_considered: List[str]
    final_reasoning: str
    action_required: bool
    intervention_prompt: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class RCAAnalysisListResponse(BaseModel):
    """List of RCA analyses."""
    analyses: List[RCAAnalysisResponse]
    total: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=RCAAnalysisResponse, status_code=201)
def create_rca_analysis(
    request: RCAAnalysisCreateRequest,
    db = Depends(get_db),
):
    """
    Create a new RCA analysis for a transaction.
    
    This endpoint stores the AI-generated root cause analysis.
    """
    try:
        # Find transaction
        try:
            transaction_uuid = UUID(request.transaction_id)
            transaction = TransactionService.get_transaction_by_id(db, transaction_uuid)
        except ValueError:
            # Not a UUID, try as transaction_id string
            transaction = TransactionService.get_transaction_by_transaction_id(
                db, request.transaction_id
            )
            if not transaction:
                raise HTTPException(status_code=404, detail="Transaction not found")
            transaction_uuid = transaction.id
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Parse RCA category
        try:
            rca_category = RCACategory(request.rca_category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid RCA category: {request.rca_category}. Valid values: {[c.value for c in RCACategory]}"
            )
        
        rca_analysis = RCAAnalysisService.create_rca_analysis(
            db,
            transaction_id=transaction_uuid,
            rca_category=rca_category,
            confidence=request.confidence,
            last_successful_checkpoint=request.last_successful_checkpoint,
            transaction_narrative=request.transaction_narrative,
            key_anomalies=request.key_anomalies,
            contradictions_observed=request.contradictions_observed,
            evidence=request.evidence,
            alternative_causes_considered=request.alternative_causes_considered,
            final_reasoning=request.final_reasoning,
            action_required=request.action_required,
            intervention_prompt=request.intervention_prompt,
        )
        
        return RCAAnalysisResponse(
            id=str(rca_analysis.id),
            transaction_id=str(rca_analysis.transaction_id),
            rca_category=rca_analysis.rca_category.value,
            confidence=rca_analysis.confidence,
            last_successful_checkpoint=rca_analysis.last_successful_checkpoint,
            transaction_narrative=rca_analysis.transaction_narrative,
            key_anomalies=rca_analysis.key_anomalies or [],
            contradictions_observed=rca_analysis.contradictions_observed or [],
            evidence=rca_analysis.evidence or [],
            alternative_causes_considered=rca_analysis.alternative_causes_considered or [],
            final_reasoning=rca_analysis.final_reasoning,
            action_required=rca_analysis.action_required,
            intervention_prompt=rca_analysis.intervention_prompt,
            created_at=rca_analysis.created_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating RCA analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transaction/{transaction_id}", response_model=RCAAnalysisResponse)
def get_rca_analysis_by_transaction(
    transaction_id: str,
    db = Depends(get_db),
):
    """Get the latest RCA analysis for a transaction."""
    try:
        # Find transaction
        try:
            transaction_uuid = UUID(transaction_id)
            transaction = TransactionService.get_transaction_by_id(db, transaction_uuid)
        except ValueError:
            # Not a UUID, try as transaction_id string
            transaction = TransactionService.get_transaction_by_transaction_id(
                db, transaction_id
            )
            if not transaction:
                raise HTTPException(status_code=404, detail="Transaction not found")
            transaction_uuid = transaction.id
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        rca_analysis = RCAAnalysisService.get_rca_analysis_by_transaction_id(
            db, transaction_uuid
        )
        
        if not rca_analysis:
            raise HTTPException(
                status_code=404,
                detail="No RCA analysis found for this transaction"
            )
        
        return RCAAnalysisResponse(
            id=str(rca_analysis.id),
            transaction_id=str(rca_analysis.transaction_id),
            rca_category=rca_analysis.rca_category.value,
            confidence=rca_analysis.confidence,
            last_successful_checkpoint=rca_analysis.last_successful_checkpoint,
            transaction_narrative=rca_analysis.transaction_narrative,
            key_anomalies=rca_analysis.key_anomalies or [],
            contradictions_observed=rca_analysis.contradictions_observed or [],
            evidence=rca_analysis.evidence or [],
            alternative_causes_considered=rca_analysis.alternative_causes_considered or [],
            final_reasoning=rca_analysis.final_reasoning,
            action_required=rca_analysis.action_required,
            intervention_prompt=rca_analysis.intervention_prompt,
            created_at=rca_analysis.created_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting RCA analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}", response_model=RCAAnalysisListResponse)
def list_rca_analyses_by_category(
    category: str,
    limit: int = 100,
    db = Depends(get_db),
):
    """List RCA analyses by category."""
    try:
        # Parse RCA category
        try:
            rca_category = RCACategory(category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid RCA category: {category}. Valid values: {[c.value for c in RCACategory]}"
            )
        
        analyses = RCAAnalysisService.list_rca_analyses_by_category(
            db, rca_category, limit=limit
        )
        
        return RCAAnalysisListResponse(
            analyses=[
                RCAAnalysisResponse(
                    id=str(a.id),
                    transaction_id=str(a.transaction_id),
                    rca_category=a.rca_category.value,
                    confidence=a.confidence,
                    last_successful_checkpoint=a.last_successful_checkpoint,
                    transaction_narrative=a.transaction_narrative,
                    key_anomalies=a.key_anomalies or [],
                    contradictions_observed=a.contradictions_observed or [],
                    evidence=a.evidence or [],
                    alternative_causes_considered=a.alternative_causes_considered or [],
                    final_reasoning=a.final_reasoning,
                    action_required=a.action_required,
                    intervention_prompt=a.intervention_prompt,
                    created_at=a.created_at.isoformat(),
                )
                for a in analyses
            ],
            total=len(analyses),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing RCA analyses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
