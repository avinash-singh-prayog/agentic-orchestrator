"""
Database service layer for Transaction RCA Agent.

Provides high-level CRUD operations for transactions, RCA analyses, tickets, etc.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from database.models import (
    Transaction,
    RCAAnalysis,
    Ticket,
    AuditLog,
    SelfHealingAction,
    TransactionStatus,
    RCACategory,
    TicketStatus,
    SelfHealingActionStatus,
    AuditActionType,
)
from database.base import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# Transaction Service
# ============================================================================

class TransactionService:
    """Service for transaction operations."""

    @staticmethod
    def create_transaction(
        db: Session,
        transaction_id: str,
        merchant_id: Optional[str] = None,
        merchant_name: Optional[str] = None,
        transaction_value: Optional[float] = None,
        currency: str = "INR",
        initiated_at: Optional[datetime] = None,
        checkpoints: Optional[List[Dict]] = None,
        merchant_config: Optional[Dict] = None,
        merchant_data: Optional[Dict] = None,
        external_signals: Optional[Dict] = None,
        risk_indicators: Optional[Dict] = None,
        observational_notes: Optional[str] = None,
    ) -> Transaction:
        """Create a new transaction record."""
        transaction = Transaction(
            transaction_id=transaction_id,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            transaction_value=transaction_value,
            currency=currency,
            initiated_at=initiated_at or datetime.utcnow(),
            checkpoints=checkpoints or [],
            merchant_config=merchant_config,
            merchant_data=merchant_data,
            external_signals=external_signals,
            risk_indicators=risk_indicators,
            observational_notes=observational_notes,
            status=TransactionStatus.PENDING,
        )
        db.add(transaction)
        db.flush()
        
        # Create audit log
        AuditLogService.create_audit_log(
            db,
            action_type=AuditActionType.TRANSACTION_DETECTED,
            transaction_id=transaction.id,
            action_description=f"Transaction {transaction_id} detected and recorded",
            action_data={"transaction_id": transaction_id},
        )
        
        return transaction

    @staticmethod
    def get_transaction_by_id(db: Session, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by UUID."""
        return db.query(Transaction).filter(Transaction.id == transaction_id).first()

    @staticmethod
    def get_transaction_by_transaction_id(db: Session, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by transaction_id string."""
        return db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()

    @staticmethod
    def list_transactions(
        db: Session,
        status: Optional[TransactionStatus] = None,
        merchant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """List transactions with optional filters."""
        query = db.query(Transaction)
        
        if status:
            query = query.filter(Transaction.status == status)
        if merchant_id:
            query = query.filter(Transaction.merchant_id == merchant_id)
        
        return query.order_by(desc(Transaction.created_at)).limit(limit).offset(offset).all()

    @staticmethod
    def update_transaction_status(
        db: Session,
        transaction_id: UUID,
        status: TransactionStatus,
    ) -> Optional[Transaction]:
        """Update transaction status."""
        transaction = TransactionService.get_transaction_by_id(db, transaction_id)
        if transaction:
            transaction.status = status
            transaction.updated_at = datetime.utcnow()
            db.flush()
        return transaction

    @staticmethod
    def count_by_status(db: Session) -> Dict[str, int]:
        """Count transactions by status."""
        results = db.query(
            Transaction.status,
            func.count(Transaction.id).label('count')
        ).group_by(Transaction.status).all()
        
        return {str(status): count for status, count in results}


# ============================================================================
# RCA Analysis Service
# ============================================================================

class RCAAnalysisService:
    """Service for RCA analysis operations."""

    @staticmethod
    def create_rca_analysis(
        db: Session,
        transaction_id: UUID,
        rca_category: RCACategory,
        confidence: float,
        last_successful_checkpoint: str,
        transaction_narrative: str,
        key_anomalies: List[str],
        contradictions_observed: List[str],
        evidence: List[str],
        alternative_causes_considered: List[str],
        final_reasoning: str,
        action_required: bool = False,
        intervention_prompt: Optional[str] = None,
    ) -> RCAAnalysis:
        """Create a new RCA analysis."""
        rca_analysis = RCAAnalysis(
            transaction_id=transaction_id,
            rca_category=rca_category,
            confidence=confidence,
            last_successful_checkpoint=last_successful_checkpoint,
            transaction_narrative=transaction_narrative,
            key_anomalies=key_anomalies,
            contradictions_observed=contradictions_observed,
            evidence=evidence,
            alternative_causes_considered=alternative_causes_considered,
            final_reasoning=final_reasoning,
            action_required=action_required,
            intervention_prompt=intervention_prompt,
        )
        db.add(rca_analysis)
        db.flush()
        
        # Update transaction status
        TransactionService.update_transaction_status(
            db, transaction_id, TransactionStatus.ANALYZED
        )
        
        # Create audit log
        AuditLogService.create_audit_log(
            db,
            action_type=AuditActionType.RCA_ANALYSIS_CREATED,
            transaction_id=transaction_id,
            action_description=f"RCA analysis created: {rca_category.value}",
            action_data={"rca_category": rca_category.value, "confidence": confidence},
        )
        
        return rca_analysis

    @staticmethod
    def get_rca_analysis_by_transaction_id(
        db: Session,
        transaction_id: UUID,
    ) -> Optional[RCAAnalysis]:
        """Get latest RCA analysis for a transaction."""
        return (
            db.query(RCAAnalysis)
            .filter(RCAAnalysis.transaction_id == transaction_id)
            .order_by(desc(RCAAnalysis.created_at))
            .first()
        )

    @staticmethod
    def list_rca_analyses_by_category(
        db: Session,
        category: RCACategory,
        limit: int = 100,
    ) -> List[RCAAnalysis]:
        """List RCA analyses by category."""
        return (
            db.query(RCAAnalysis)
            .filter(RCAAnalysis.rca_category == category)
            .order_by(desc(RCAAnalysis.created_at))
            .limit(limit)
            .all()
        )


# ============================================================================
# Ticket Service
# ============================================================================

class TicketService:
    """Service for ticket operations."""

    @staticmethod
    def generate_ticket_number() -> str:
        """Generate a unique ticket number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"TKT-{timestamp}"

    @staticmethod
    def create_ticket(
        db: Session,
        transaction_id: UUID,
        title: str,
        description: Optional[str] = None,
        rca_summary: Optional[str] = None,
        priority: str = "medium",
        owning_team: Optional[str] = None,
        actions_attempted: Optional[List[Dict]] = None,
    ) -> Ticket:
        """Create a new ticket."""
        ticket = Ticket(
            transaction_id=transaction_id,
            ticket_number=TicketService.generate_ticket_number(),
            title=title,
            description=description,
            rca_summary=rca_summary,
            priority=priority,
            owning_team=owning_team,
            actions_attempted=actions_attempted or [],
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        db.flush()
        
        # Update transaction status
        TransactionService.update_transaction_status(
            db, transaction_id, TransactionStatus.ESCALATED
        )
        
        # Create audit log
        AuditLogService.create_audit_log(
            db,
            action_type=AuditActionType.TICKET_CREATED,
            transaction_id=transaction_id,
            action_description=f"Ticket created: {ticket.ticket_number}",
            action_data={"ticket_number": ticket.ticket_number, "title": title},
        )
        
        return ticket

    @staticmethod
    def get_ticket_by_id(db: Session, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket by UUID."""
        return db.query(Ticket).filter(Ticket.id == ticket_id).first()

    @staticmethod
    def get_ticket_by_number(db: Session, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number."""
        return db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    @staticmethod
    def list_tickets(
        db: Session,
        status: Optional[TicketStatus] = None,
        transaction_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Ticket]:
        """List tickets with optional filters."""
        query = db.query(Ticket)
        
        if status:
            query = query.filter(Ticket.status == status)
        if transaction_id:
            query = query.filter(Ticket.transaction_id == transaction_id)
        
        return query.order_by(desc(Ticket.created_at)).limit(limit).offset(offset).all()

    @staticmethod
    def update_ticket_status(
        db: Session,
        ticket_id: UUID,
        status: TicketStatus,
        resolved_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[Ticket]:
        """Update ticket status."""
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        if ticket:
            ticket.status = status
            if status == TicketStatus.RESOLVED or status == TicketStatus.CLOSED:
                ticket.resolved_at = datetime.utcnow()
                ticket.resolved_by = resolved_by
                ticket.resolution_notes = resolution_notes
            ticket.updated_at = datetime.utcnow()
            db.flush()
            
            # Create audit log
            AuditLogService.create_audit_log(
                db,
                action_type=AuditActionType.TICKET_UPDATED,
                transaction_id=ticket.transaction_id,
                action_description=f"Ticket {ticket.ticket_number} updated to {status.value}",
                action_data={"ticket_id": str(ticket_id), "status": status.value},
            )
        
        return ticket


# ============================================================================
# Self-Healing Action Service
# ============================================================================

class SelfHealingActionService:
    """Service for self-healing action operations."""

    @staticmethod
    def create_action(
        db: Session,
        transaction_id: UUID,
        action_type: str,
        action_params: Optional[Dict] = None,
        max_attempts: int = 3,
    ) -> SelfHealingAction:
        """Create a new self-healing action."""
        action = SelfHealingAction(
            transaction_id=transaction_id,
            action_type=action_type,
            action_params=action_params or {},
            status=SelfHealingActionStatus.PENDING,
            attempt_number=1,
            max_attempts=max_attempts,
            started_at=datetime.utcnow(),
        )
        db.add(action)
        db.flush()
        
        # Create audit log
        AuditLogService.create_audit_log(
            db,
            action_type=AuditActionType.SELF_HEALING_ATTEMPTED,
            transaction_id=transaction_id,
            action_description=f"Self-healing action started: {action_type}",
            action_data={"action_type": action_type, "action_params": action_params},
        )
        
        return action

    @staticmethod
    def update_action_status(
        db: Session,
        action_id: UUID,
        status: SelfHealingActionStatus,
        action_result: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ) -> Optional[SelfHealingAction]:
        """Update self-healing action status."""
        action = db.query(SelfHealingAction).filter(SelfHealingAction.id == action_id).first()
        if action:
            action.status = status
            if action_result:
                action.action_result = action_result
            if error_message:
                action.error_message = error_message
            if status in [SelfHealingActionStatus.SUCCESS, SelfHealingActionStatus.FAILED, SelfHealingActionStatus.ROLLED_BACK]:
                action.completed_at = datetime.utcnow()
            db.flush()
            
            # Create audit log
            audit_type = (
                AuditActionType.SELF_HEALING_SUCCEEDED
                if status == SelfHealingActionStatus.SUCCESS
                else AuditActionType.SELF_HEALING_FAILED
            )
            AuditLogService.create_audit_log(
                db,
                action_type=audit_type,
                transaction_id=action.transaction_id,
                action_description=f"Self-healing action {action.action_type} {status.value}",
                action_data={"action_id": str(action_id), "status": status.value},
                success=(status == SelfHealingActionStatus.SUCCESS),
                error_message=error_message,
            )
        
        return action

    @staticmethod
    def list_actions_by_transaction(
        db: Session,
        transaction_id: UUID,
    ) -> List[SelfHealingAction]:
        """List all self-healing actions for a transaction."""
        return (
            db.query(SelfHealingAction)
            .filter(SelfHealingAction.transaction_id == transaction_id)
            .order_by(desc(SelfHealingAction.created_at))
            .all()
        )


# ============================================================================
# Audit Log Service
# ============================================================================

class AuditLogService:
    """Service for audit log operations."""

    @staticmethod
    def create_audit_log(
        db: Session,
        action_type: AuditActionType,
        action_description: str,
        transaction_id: Optional[UUID] = None,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        action_data: Optional[Dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        audit_log = AuditLog(
            action_type=action_type,
            transaction_id=transaction_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action_description=action_description,
            action_data=action_data or {},
            success=success,
            error_message=error_message,
        )
        db.add(audit_log)
        db.flush()
        return audit_log

    @staticmethod
    def list_audit_logs(
        db: Session,
        transaction_id: Optional[UUID] = None,
        action_type: Optional[AuditActionType] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[AuditLog]:
        """List audit logs with optional filters."""
        query = db.query(AuditLog)
        
        if transaction_id:
            query = query.filter(AuditLog.transaction_id == transaction_id)
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset).all()
