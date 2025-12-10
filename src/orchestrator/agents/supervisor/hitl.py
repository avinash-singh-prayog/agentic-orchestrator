"""
Human-in-the-Loop (HITL) Integration

Implements LangGraph interrupt mechanism for orders requiring human approval.
Combines:
- LangGraph NodeInterrupt for state suspension
- Identity Service for out-of-band approval workflow
- Graph resume on approval
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from langgraph.types import Command

logger = logging.getLogger(__name__)


@dataclass
class HITLInterrupt:
    """
    Human-in-the-Loop interrupt request.
    
    Created when an action requires human approval before proceeding.
    The workflow suspends until approval is received.
    """
    
    interrupt_id: str
    order_id: str
    reason: str
    required_action: str
    context: dict[str, Any]
    created_at: datetime
    approval_status: str = "pending"  # pending, approved, rejected
    approved_by: str | None = None
    approved_at: datetime | None = None
    
    @classmethod
    def create(
        cls,
        order_id: str,
        reason: str,
        action: str,
        context: dict[str, Any],
    ) -> "HITLInterrupt":
        """Create a new HITL interrupt."""
        return cls(
            interrupt_id=f"hitl_{uuid4().hex[:12]}",
            order_id=order_id,
            reason=reason,
            required_action=action,
            context=context,
            created_at=datetime.utcnow(),
        )


class HITLManager:
    """
    Manages Human-in-the-Loop workflows.
    
    Handles:
    - Creating approval requests
    - Storing pending interrupts
    - Processing approvals/rejections
    - Resuming workflows after approval
    """
    
    def __init__(self, identity_service=None):
        """
        Initialize the HITL manager.
        
        Args:
            identity_service: Optional IdentityService for production integration.
        """
        self._pending_interrupts: dict[str, HITLInterrupt] = {}
        self._identity_service = identity_service
        logger.info("Initialized HITLManager")
    
    async def create_interrupt(
        self,
        order_id: str,
        reason: str,
        action: str,
        context: dict[str, Any],
    ) -> HITLInterrupt:
        """
        Create and store an interrupt request.
        
        Args:
            order_id: The order requiring approval.
            reason: Why approval is needed.
            action: The action requiring approval (e.g., "book_shipment").
            context: Additional context (order value, etc.).
            
        Returns:
            Created HITLInterrupt.
        """
        interrupt = HITLInterrupt.create(
            order_id=order_id,
            reason=reason,
            action=action,
            context=context,
        )
        
        self._pending_interrupts[interrupt.interrupt_id] = interrupt
        
        # If identity service is available, create formal approval request
        if self._identity_service:
            await self._identity_service.create_approval_request(
                task_type=action,
                resource_id=order_id,
                requester_did=f"did:agntcy:agent:supervisor",
                amount=context.get("order_value"),
                currency=context.get("currency", "USD"),
            )
        
        logger.info(f"Created HITL interrupt: {interrupt.interrupt_id} for order {order_id}")
        return interrupt
    
    async def get_interrupt(self, interrupt_id: str) -> HITLInterrupt | None:
        """Get a pending interrupt by ID."""
        return self._pending_interrupts.get(interrupt_id)
    
    async def get_interrupt_by_order(self, order_id: str) -> HITLInterrupt | None:
        """Get a pending interrupt for an order."""
        for interrupt in self._pending_interrupts.values():
            if interrupt.order_id == order_id and interrupt.approval_status == "pending":
                return interrupt
        return None
    
    async def approve(
        self,
        interrupt_id: str,
        approved_by: str,
    ) -> HITLInterrupt:
        """
        Approve a pending interrupt.
        
        Args:
            interrupt_id: The interrupt to approve.
            approved_by: DID or identifier of the approver.
            
        Returns:
            Updated interrupt.
        """
        interrupt = self._pending_interrupts.get(interrupt_id)
        if not interrupt:
            raise ValueError(f"Interrupt not found: {interrupt_id}")
        
        if interrupt.approval_status != "pending":
            raise ValueError(f"Interrupt is not pending: {interrupt.approval_status}")
        
        interrupt.approval_status = "approved"
        interrupt.approved_by = approved_by
        interrupt.approved_at = datetime.utcnow()
        
        logger.info(f"Approved interrupt: {interrupt_id} by {approved_by}")
        return interrupt
    
    async def reject(
        self,
        interrupt_id: str,
        rejected_by: str,
        reason: str = "",
    ) -> HITLInterrupt:
        """
        Reject a pending interrupt.
        
        Args:
            interrupt_id: The interrupt to reject.
            rejected_by: DID or identifier of the rejector.
            reason: Reason for rejection.
            
        Returns:
            Updated interrupt.
        """
        interrupt = self._pending_interrupts.get(interrupt_id)
        if not interrupt:
            raise ValueError(f"Interrupt not found: {interrupt_id}")
        
        interrupt.approval_status = "rejected"
        interrupt.approved_by = rejected_by
        interrupt.approved_at = datetime.utcnow()
        
        logger.info(f"Rejected interrupt: {interrupt_id} by {rejected_by}, reason: {reason}")
        return interrupt
    
    def create_resume_command(self, interrupt: HITLInterrupt) -> Command:
        """
        Create a LangGraph Command to resume the workflow.
        
        Args:
            interrupt: The approved interrupt.
            
        Returns:
            LangGraph Command with resume data.
        """
        return Command(
            resume={
                "interrupt_id": interrupt.interrupt_id,
                "approval_status": interrupt.approval_status,
                "approved_by": interrupt.approved_by,
                "approved_at": interrupt.approved_at.isoformat() if interrupt.approved_at else None,
            }
        )


# Global HITL manager instance
_hitl_manager: HITLManager | None = None


def get_hitl_manager() -> HITLManager:
    """Get the global HITL manager instance."""
    global _hitl_manager
    if _hitl_manager is None:
        _hitl_manager = HITLManager()
    return _hitl_manager


def set_hitl_manager(manager: HITLManager) -> None:
    """Set the global HITL manager instance."""
    global _hitl_manager
    _hitl_manager = manager
