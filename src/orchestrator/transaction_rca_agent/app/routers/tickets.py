"""
Ticket management API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from database.base import get_db
from database.models import TicketStatus
from services.database_service import TicketService, TransactionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TicketCreateRequest(BaseModel):
    """Request to create a ticket."""
    transaction_id: str = Field(..., description="Transaction ID (UUID or transaction_id string)")
    title: str
    description: Optional[str] = None
    rca_summary: Optional[str] = None
    priority: str = "medium"
    owning_team: Optional[str] = None
    actions_attempted: Optional[List[dict]] = None


class TicketResponse(BaseModel):
    """Ticket response model."""
    id: str
    transaction_id: str
    ticket_number: str
    status: str
    priority: str
    title: str
    description: Optional[str]
    rca_summary: Optional[str]
    owning_team: Optional[str]
    assigned_to: Optional[str]
    actions_attempted: List[dict]
    resolution_notes: Optional[str]
    resolved_at: Optional[str]
    resolved_by: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    """List of tickets."""
    tickets: List[TicketResponse]
    total: int


class TicketStatusUpdateRequest(BaseModel):
    """Request to update ticket status."""
    status: str
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(
    request: TicketCreateRequest,
    db = Depends(get_db),
):
    """
    Create a new ticket for human intervention.
    
    This endpoint is used when escalation is required.
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
        
        ticket = TicketService.create_ticket(
            db,
            transaction_id=transaction_uuid,
            title=request.title,
            description=request.description,
            rca_summary=request.rca_summary,
            priority=request.priority,
            owning_team=request.owning_team,
            actions_attempted=request.actions_attempted or [],
        )
        
        return TicketResponse(
            id=str(ticket.id),
            transaction_id=str(ticket.transaction_id),
            ticket_number=ticket.ticket_number,
            status=ticket.status.value,
            priority=ticket.priority,
            title=ticket.title,
            description=ticket.description,
            rca_summary=ticket.rca_summary,
            owning_team=ticket.owning_team,
            assigned_to=ticket.assigned_to,
            actions_attempted=ticket.actions_attempted or [],
            resolution_notes=ticket.resolution_notes,
            resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            resolved_by=ticket.resolved_by,
            created_at=ticket.created_at.isoformat(),
            updated_at=ticket.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: str,
    db = Depends(get_db),
):
    """Get a ticket by ID (UUID) or ticket number."""
    try:
        # Try as UUID first
        try:
            uuid_id = UUID(ticket_id)
            ticket = TicketService.get_ticket_by_id(db, uuid_id)
        except ValueError:
            # Not a UUID, try as ticket number
            ticket = TicketService.get_ticket_by_number(db, ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return TicketResponse(
            id=str(ticket.id),
            transaction_id=str(ticket.transaction_id),
            ticket_number=ticket.ticket_number,
            status=ticket.status.value,
            priority=ticket.priority,
            title=ticket.title,
            description=ticket.description,
            rca_summary=ticket.rca_summary,
            owning_team=ticket.owning_team,
            assigned_to=ticket.assigned_to,
            actions_attempted=ticket.actions_attempted or [],
            resolution_notes=ticket.resolution_notes,
            resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            resolved_by=ticket.resolved_by,
            created_at=ticket.created_at.isoformat(),
            updated_at=ticket.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status: Optional[str] = None,
    transaction_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db = Depends(get_db),
):
    """List tickets with optional filters."""
    try:
        # Parse status enum
        status_enum = None
        if status:
            try:
                status_enum = TicketStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: {[s.value for s in TicketStatus]}"
                )
        
        # Parse transaction_id
        transaction_uuid = None
        if transaction_id:
            try:
                transaction_uuid = UUID(transaction_id)
            except ValueError:
                # Try as transaction_id string
                transaction = TransactionService.get_transaction_by_transaction_id(
                    db, transaction_id
                )
                if transaction:
                    transaction_uuid = transaction.id
                else:
                    raise HTTPException(status_code=404, detail="Transaction not found")
        
        tickets = TicketService.list_tickets(
            db,
            status=status_enum,
            transaction_id=transaction_uuid,
            limit=limit,
            offset=offset,
        )
        
        return TicketListResponse(
            tickets=[
                TicketResponse(
                    id=str(t.id),
                    transaction_id=str(t.transaction_id),
                    ticket_number=t.ticket_number,
                    status=t.status.value,
                    priority=t.priority,
                    title=t.title,
                    description=t.description,
                    rca_summary=t.rca_summary,
                    owning_team=t.owning_team,
                    assigned_to=t.assigned_to,
                    actions_attempted=t.actions_attempted or [],
                    resolution_notes=t.resolution_notes,
                    resolved_at=t.resolved_at.isoformat() if t.resolved_at else None,
                    resolved_by=t.resolved_by,
                    created_at=t.created_at.isoformat(),
                    updated_at=t.updated_at.isoformat(),
                )
                for t in tickets
            ],
            total=len(tickets),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: str,
    request: TicketStatusUpdateRequest,
    db = Depends(get_db),
):
    """Update ticket status."""
    try:
        # Parse ticket_id
        try:
            uuid_id = UUID(ticket_id)
        except ValueError:
            # Try to find by ticket number
            ticket = TicketService.get_ticket_by_number(db, ticket_id)
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")
            uuid_id = ticket.id
        
        # Parse status enum
        try:
            status_enum = TicketStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}. Valid values: {[s.value for s in TicketStatus]}"
            )
        
        ticket = TicketService.update_ticket_status(
            db,
            uuid_id,
            status_enum,
            resolved_by=request.resolved_by,
            resolution_notes=request.resolution_notes,
        )
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return TicketResponse(
            id=str(ticket.id),
            transaction_id=str(ticket.transaction_id),
            ticket_number=ticket.ticket_number,
            status=ticket.status.value,
            priority=ticket.priority,
            title=ticket.title,
            description=ticket.description,
            rca_summary=ticket.rca_summary,
            owning_team=ticket.owning_team,
            assigned_to=ticket.assigned_to,
            actions_attempted=ticket.actions_attempted or [],
            resolution_notes=ticket.resolution_notes,
            resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            resolved_by=ticket.resolved_by,
            created_at=ticket.created_at.isoformat(),
            updated_at=ticket.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
