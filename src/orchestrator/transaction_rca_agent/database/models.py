"""
Database models for Transaction RCA Agent.

SQLAlchemy models for:
- Transactions (unprocessed transaction tracking)
- RCA Analysis (analysis results)
- Tickets (human intervention tickets)
- Audit Logs (action audit trail)
- Self-Healing Actions (automated remediation attempts)
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from .base import Base


# ============================================================================
# Enums
# ============================================================================

class TransactionStatus(str, enum.Enum):
    """Transaction processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED = "failed"


class RCACategory(str, enum.Enum):
    """RCA category classification."""
    SYNC_ISSUES = "Sync Issues"
    CONFIGURATION_ISSUES = "Configuration Issues"
    ROUTING_ISSUES = "Routing Issues"
    DEPENDENCY_FAILURES = "Dependency Failures"
    MERCHANT_DATA_ISSUES = "Merchant Data Issues"
    COMPLIANCE_RISK_HOLDS = "Compliance / Risk Holds"
    UNKNOWN_SYSTEM_DEFECT = "Unknown / System Defect"


class TicketStatus(str, enum.Enum):
    """Ticket status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SelfHealingActionStatus(str, enum.Enum):
    """Self-healing action status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class AuditActionType(str, enum.Enum):
    """Audit log action types."""
    TRANSACTION_DETECTED = "transaction_detected"
    RCA_ANALYSIS_CREATED = "rca_analysis_created"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    SELF_HEALING_ATTEMPTED = "self_healing_attempted"
    SELF_HEALING_SUCCEEDED = "self_healing_succeeded"
    SELF_HEALING_FAILED = "self_healing_failed"
    MANUAL_INTERVENTION = "manual_intervention"


# ============================================================================
# Models
# ============================================================================

class Transaction(Base):
    """
    Unprocessed transaction record.
    
    Tracks transactions that need RCA analysis.
    """
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False, index=True)
    
    # Transaction metadata
    merchant_id = Column(String(255), index=True)
    merchant_name = Column(String(255))
    transaction_value = Column(Float)
    currency = Column(String(10), default="INR")
    
    # Timing
    initiated_at = Column(DateTime(timezone=True))
    sla_breach_time = Column(DateTime(timezone=True))
    age_days = Column(Integer, default=0)  # T+0, T+1, T+2, etc.
    
    # Transaction context (stored as JSON)
    checkpoints = Column(JSON)  # List of TransactionCheckpoint
    merchant_config = Column(JSON)
    merchant_data = Column(JSON)
    external_signals = Column(JSON)
    risk_indicators = Column(JSON)
    observational_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    rca_analyses = relationship("RCAAnalysis", back_populates="transaction", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="transaction", cascade="all, delete-orphan")
    self_healing_actions = relationship("SelfHealingAction", back_populates="transaction", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, transaction_id={self.transaction_id}, status={self.status})>"


class RCAAnalysis(Base):
    """
    RCA analysis result for a transaction.
    
    Stores the AI-generated root cause analysis.
    """
    __tablename__ = "rca_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True)
    
    # RCA Classification
    rca_category = Column(SQLEnum(RCACategory), nullable=False, index=True)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    last_successful_checkpoint = Column(String(255), nullable=False)
    
    # Analysis details
    transaction_narrative = Column(Text, nullable=False)
    key_anomalies = Column(JSON)  # List of strings
    contradictions_observed = Column(JSON)  # List of strings
    evidence = Column(JSON)  # List of strings
    alternative_causes_considered = Column(JSON)  # List of strings
    final_reasoning = Column(Text, nullable=False)
    
    # Human intervention
    action_required = Column(Boolean, default=False, nullable=False)
    intervention_prompt = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="rca_analyses")
    
    def __repr__(self):
        return f"<RCAAnalysis(id={self.id}, transaction_id={self.transaction_id}, category={self.rca_category})>"


class Ticket(Base):
    """
    Human intervention ticket.
    
    Created when escalation is required or human confirmation needed.
    """
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True)
    
    # Ticket details
    ticket_number = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True)
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Ownership
    owning_team = Column(String(255))
    assigned_to = Column(String(255))
    
    # Content
    title = Column(String(500), nullable=False)
    description = Column(Text)
    rca_summary = Column(Text)  # Summary from RCA analysis
    actions_attempted = Column(JSON)  # List of self-healing actions attempted
    
    # Resolution
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="tickets")
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, ticket_number={self.ticket_number}, status={self.status})>"


class SelfHealingAction(Base):
    """
    Self-healing action attempt.
    
    Tracks automated remediation attempts.
    """
    __tablename__ = "self_healing_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(100), nullable=False, index=True)  # e.g., "re_sync", "re_trigger", "config_fix"
    status = Column(SQLEnum(SelfHealingActionStatus), default=SelfHealingActionStatus.PENDING, nullable=False, index=True)
    
    # Action parameters and results
    action_params = Column(JSON)  # Parameters used for the action
    action_result = Column(JSON)  # Result of the action
    error_message = Column(Text)
    
    # Retry tracking
    attempt_number = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="self_healing_actions")
    
    def __repr__(self):
        return f"<SelfHealingAction(id={self.id}, action_type={self.action_type}, status={self.status})>"


class AuditLog(Base):
    """
    Audit log for all actions.
    
    Provides full audit trail for compliance and debugging.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Action details
    action_type = Column(SQLEnum(AuditActionType), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), index=True)
    
    # Actor
    actor_type = Column(String(50))  # "system", "user", "agent"
    actor_id = Column(String(255))
    
    # Action details
    action_description = Column(Text, nullable=False)
    action_data = Column(JSON)  # Additional context data
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action_type={self.action_type}, created_at={self.created_at})>"
