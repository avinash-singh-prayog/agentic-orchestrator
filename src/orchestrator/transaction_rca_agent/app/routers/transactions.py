"""
Transaction management API endpoints.
"""

import logging
from typing import List, Optional, Any, Dict
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict

from database.base import get_db
from database.models import TransactionStatus
from services.database_service import TransactionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TransactionCheckpointRequest(BaseModel):
    """Transaction checkpoint data - flexible format accepting any fields."""
    model_config = ConfigDict(extra="allow")  # Allow arbitrary fields
    
    checkpoint_name: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    details: Optional[dict] = None


class TransactionCreateRequest(BaseModel):
    """Request to create a transaction - accepts any transaction format."""
    model_config = ConfigDict(extra="allow")  # Allow arbitrary fields
    
    transaction_id: Optional[str] = Field(None, description="Unique transaction identifier")
    merchant_id: Optional[str] = None
    merchant_name: Optional[str] = None
    transaction_value: Optional[float] = None
    currency: Optional[str] = "INR"
    initiated_at: Optional[str] = None
    checkpoints: Optional[List[Any]] = None  # Accept any checkpoint format
    merchant_config: Optional[dict] = None
    merchant_data: Optional[dict] = None
    external_signals: Optional[dict] = None
    risk_indicators: Optional[dict] = None
    observational_notes: Optional[str] = None


class TransactionResponse(BaseModel):
    """Transaction response model."""
    id: str
    transaction_id: str
    status: str
    merchant_id: Optional[str]
    merchant_name: Optional[str]
    transaction_value: Optional[float]
    currency: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """List of transactions."""
    transactions: List[TransactionResponse]
    total: int


class TransactionStatusUpdateRequest(BaseModel):
    """Request to update transaction status."""
    status: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(
    request: TransactionCreateRequest,
    db = Depends(get_db),
):
    """
    Create a new unprocessed transaction record.
    
    This endpoint is used to register transactions that need RCA analysis.
    Accepts any transaction format - all fields are optional.
    """
    try:
        # Generate transaction_id if not provided
        transaction_id = request.transaction_id
        if not transaction_id:
            import uuid
            transaction_id = f"TXN-{uuid.uuid4().hex[:8]}"
        
        # Check if transaction already exists (only if transaction_id was provided)
        if request.transaction_id:
            existing = TransactionService.get_transaction_by_transaction_id(
                db, transaction_id
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Transaction {transaction_id} already exists"
                )
        
        # Convert checkpoints to dict format - handle any format
        checkpoints = None
        if request.checkpoints:
            if isinstance(request.checkpoints, list):
                checkpoints = []
                for cp in request.checkpoints:
                    if isinstance(cp, dict):
                        checkpoints.append(cp)
                    elif hasattr(cp, 'model_dump'):
                        checkpoints.append(cp.model_dump())
                    else:
                        checkpoints.append({"data": str(cp)})
            else:
                checkpoints = [{"data": str(request.checkpoints)}]
        
        # Parse initiated_at if provided
        from datetime import datetime
        initiated_at = None
        if request.initiated_at:
            try:
                initiated_at = datetime.fromisoformat(request.initiated_at.replace('Z', '+00:00'))
            except Exception:
                pass
        
        transaction = TransactionService.create_transaction(
            db,
            transaction_id=transaction_id,
            merchant_id=request.merchant_id,
            merchant_name=request.merchant_name,
            transaction_value=request.transaction_value,
            currency=request.currency or "INR",
            initiated_at=initiated_at,
            checkpoints=checkpoints,
            merchant_config=request.merchant_config,
            merchant_data=request.merchant_data,
            external_signals=request.external_signals,
            risk_indicators=request.risk_indicators,
            observational_notes=request.observational_notes,
        )
        
        return TransactionResponse(
            id=str(transaction.id),
            transaction_id=transaction.transaction_id,
            status=transaction.status.value,
            merchant_id=transaction.merchant_id,
            merchant_name=transaction.merchant_name,
            transaction_value=transaction.transaction_value,
            currency=transaction.currency,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db = Depends(get_db),
):
    """Get a transaction by ID (UUID or transaction_id string)."""
    try:
        # Try as UUID first
        try:
            uuid_id = UUID(transaction_id)
            transaction = TransactionService.get_transaction_by_id(db, uuid_id)
        except ValueError:
            # Not a UUID, try as transaction_id string
            transaction = TransactionService.get_transaction_by_transaction_id(
                db, transaction_id
            )
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return TransactionResponse(
            id=str(transaction.id),
            transaction_id=transaction.transaction_id,
            status=transaction.status.value,
            merchant_id=transaction.merchant_id,
            merchant_name=transaction.merchant_name,
            transaction_value=transaction.transaction_value,
            currency=transaction.currency,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    status: Optional[str] = None,
    merchant_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db = Depends(get_db),
):
    """List transactions with optional filters."""
    try:
        # Parse status enum
        status_enum = None
        if status:
            try:
                status_enum = TransactionStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: {[s.value for s in TransactionStatus]}"
                )
        
        transactions = TransactionService.list_transactions(
            db,
            status=status_enum,
            merchant_id=merchant_id,
            limit=limit,
            offset=offset,
        )
        
        return TransactionListResponse(
            transactions=[
                TransactionResponse(
                    id=str(t.id),
                    transaction_id=t.transaction_id,
                    status=t.status.value,
                    merchant_id=t.merchant_id,
                    merchant_name=t.merchant_name,
                    transaction_value=t.transaction_value,
                    currency=t.currency,
                    created_at=t.created_at.isoformat(),
                    updated_at=t.updated_at.isoformat(),
                )
                for t in transactions
            ],
            total=len(transactions),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
def update_transaction_status(
    transaction_id: str,
    request: TransactionStatusUpdateRequest,
    db = Depends(get_db),
):
    """Update transaction status."""
    try:
        # Parse transaction_id
        try:
            uuid_id = UUID(transaction_id)
        except ValueError:
            # Try to find by transaction_id string
            transaction = TransactionService.get_transaction_by_transaction_id(
                db, transaction_id
            )
            if not transaction:
                raise HTTPException(status_code=404, detail="Transaction not found")
            uuid_id = transaction.id
        
        # Parse status enum
        try:
            status_enum = TransactionStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}. Valid values: {[s.value for s in TransactionStatus]}"
            )
        
        transaction = TransactionService.update_transaction_status(
            db, uuid_id, status_enum
        )
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return TransactionResponse(
            id=str(transaction.id),
            transaction_id=transaction.transaction_id,
            status=transaction.status.value,
            merchant_id=transaction.merchant_id,
            merchant_name=transaction.merchant_name,
            transaction_value=transaction.transaction_value,
            currency=transaction.currency,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
def get_transaction_stats(db = Depends(get_db)):
    """Get transaction statistics summary."""
    try:
        counts = TransactionService.count_by_status(db)
        return {"status_counts": counts}
    except Exception as e:
        logger.error(f"Error getting transaction stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
