"""
Tests for database models.
"""

import pytest
from datetime import datetime
from uuid import uuid4

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


def test_transaction_creation(db_session):
    """Test creating a transaction."""
    transaction = Transaction(
        transaction_id="TXN_001",
        merchant_id="MERCHANT_001",
        merchant_name="Test Merchant",
        transaction_value=1000.0,
        currency="INR",
        initiated_at=datetime.utcnow(),
        status=TransactionStatus.PENDING,
    )
    db_session.add(transaction)
    db_session.commit()
    
    assert transaction.id is not None
    assert transaction.transaction_id == "TXN_001"
    assert transaction.status == TransactionStatus.PENDING
    assert transaction.created_at is not None


def test_rca_analysis_creation(db_session, test_transaction):
    """Test creating an RCA analysis."""
    rca_analysis = RCAAnalysis(
        transaction_id=test_transaction.id,
        rca_category=RCACategory.SYNC_ISSUES,
        confidence=0.95,
        last_successful_checkpoint="authorization",
        transaction_narrative="Transaction stuck after authorization",
        key_anomalies=["Missing ledger entry"],
        contradictions_observed=[],
        evidence=["Checkpoint data shows authorization success"],
        alternative_causes_considered=["Configuration Issues"],
        final_reasoning="Sync issue between systems",
        action_required=True,
        intervention_prompt="Please review and approve ticket creation",
    )
    db_session.add(rca_analysis)
    db_session.commit()
    
    assert rca_analysis.id is not None
    assert rca_analysis.transaction_id == test_transaction.id
    assert rca_analysis.rca_category == RCACategory.SYNC_ISSUES
    assert rca_analysis.confidence == 0.95


def test_ticket_creation(db_session, test_transaction):
    """Test creating a ticket."""
    ticket = Ticket(
        transaction_id=test_transaction.id,
        ticket_number="TKT-20240101000001",
        title="Transaction TXN_TEST_001 requires manual intervention",
        description="Transaction is stuck in routing",
        status=TicketStatus.OPEN,
        priority="high",
        owning_team="Operations",
    )
    db_session.add(ticket)
    db_session.commit()
    
    assert ticket.id is not None
    assert ticket.transaction_id == test_transaction.id
    assert ticket.status == TicketStatus.OPEN
    assert ticket.ticket_number == "TKT-20240101000001"


def test_audit_log_creation(db_session, test_transaction):
    """Test creating an audit log."""
    audit_log = AuditLog(
        action_type=AuditActionType.TRANSACTION_DETECTED,
        transaction_id=test_transaction.id,
        actor_type="system",
        action_description="Transaction detected",
        action_data={"transaction_id": "TXN_TEST_001"},
        success=True,
    )
    db_session.add(audit_log)
    db_session.commit()
    
    assert audit_log.id is not None
    assert audit_log.transaction_id == test_transaction.id
    assert audit_log.action_type == AuditActionType.TRANSACTION_DETECTED
    assert audit_log.success is True


def test_self_healing_action_creation(db_session, test_transaction):
    """Test creating a self-healing action."""
    action = SelfHealingAction(
        transaction_id=test_transaction.id,
        action_type="re_sync",
        status=SelfHealingActionStatus.PENDING,
        action_params={"system": "ledger"},
        attempt_number=1,
        max_attempts=3,
        started_at=datetime.utcnow(),
    )
    db_session.add(action)
    db_session.commit()
    
    assert action.id is not None
    assert action.transaction_id == test_transaction.id
    assert action.action_type == "re_sync"
    assert action.status == SelfHealingActionStatus.PENDING


def test_transaction_relationships(db_session, test_transaction):
    """Test transaction relationships."""
    # Create RCA analysis
    rca_analysis = RCAAnalysis(
        transaction_id=test_transaction.id,
        rca_category=RCACategory.SYNC_ISSUES,
        confidence=0.9,
        last_successful_checkpoint="authorization",
        transaction_narrative="Test narrative",
        key_anomalies=[],
        contradictions_observed=[],
        evidence=[],
        alternative_causes_considered=[],
        final_reasoning="Test reasoning",
    )
    db_session.add(rca_analysis)
    
    # Create ticket
    ticket = Ticket(
        transaction_id=test_transaction.id,
        ticket_number="TKT-001",
        title="Test Ticket",
        status=TicketStatus.OPEN,
    )
    db_session.add(ticket)
    db_session.commit()
    
    # Refresh and check relationships
    db_session.refresh(test_transaction)
    assert len(test_transaction.rca_analyses) == 1
    assert len(test_transaction.tickets) == 1
    assert test_transaction.rca_analyses[0].id == rca_analysis.id
    assert test_transaction.tickets[0].id == ticket.id
