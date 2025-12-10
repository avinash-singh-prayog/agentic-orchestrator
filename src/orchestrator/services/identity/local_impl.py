"""
Local Identity Service Implementation

In-memory implementation of the IdentityService interface for V1/development.
This provides all the functionality needed for testing and local development
without requiring an external identity service.

For production V2, replace with AGNTCYIdentityService that integrates
with the full AGNTCY Identity Service.
"""

import logging
from datetime import datetime
from uuid import uuid4

from orchestrator.services.identity.interface import IdentityService
from orchestrator.services.identity.models import (
    ApprovalRequest,
    Badge,
    CredentialSubject,
    IdentityServiceApp,
    Policy,
    Proof,
    Rule,
    Task,
    VerifiableCredential,
)

logger = logging.getLogger(__name__)


class LocalIdentityService(IdentityService):
    """
    In-memory implementation of the Identity Service.
    
    Suitable for:
    - Local development
    - Testing
    - POC deployments
    
    Limitations:
    - Data is not persisted across restarts
    - No actual cryptographic verification
    - No external identity provider integration
    """
    
    def __init__(self):
        """Initialize the local identity service with default data."""
        self._apps: dict[str, IdentityServiceApp] = {}
        self._badges: dict[str, Badge] = {}
        self._policies: dict[str, Policy] = {}
        self._approval_requests: dict[str, ApprovalRequest] = {}
        
        # Initialize with default agents
        self._initialize_default_agents()
        
        logger.info("Initialized LocalIdentityService")
    
    def _initialize_default_agents(self) -> None:
        """Set up default agent registrations."""
        default_agents = [
            ("supervisor", "Orchestrator Supervisor", ["orchestration", "planning"]),
            ("serviceability", "Serviceability Agent", ["address_validation", "embargo_check"]),
            ("rate", "Rate Negotiation Agent", ["quote_generation", "rate_comparison"]),
            ("carrier", "Carrier Execution Agent", ["booking", "tracking"]),
        ]
        
        for agent_id, name, capabilities in default_agents:
            app = IdentityServiceApp(
                id=agent_id,
                name=name,
                description=f"Default {name}",
                type="agent",
                api_key=f"key_{agent_id}_{uuid4().hex[:8]}",
                status="active",
            )
            self._apps[agent_id] = app
            
            # Create badge
            badge = self._create_badge_internal(
                app_id=agent_id,
                agent_url=f"http://{agent_id}-agent:9000",
                capabilities=capabilities,
            )
            self._badges[agent_id] = badge
        
        # Create default policies
        self._create_default_policies()
    
    def _create_default_policies(self) -> None:
        """Create default TBAC policies."""
        # High-value order approval policy
        high_value_policy = Policy(
            id="policy_high_value_approval",
            name="High Value Order Approval",
            description="Requires approval for orders above configured threshold",
            assigned_to="carrier",
            rules=[
                Rule(
                    id="rule_auto_approve_low",
                    name="Auto-approve low value",
                    description="Automatically approve orders below threshold",
                    policy_id="policy_high_value_approval",
                    tasks=[Task(name="book_shipment", tool_name="book_shipment")],
                    action="allow",
                    needs_approval=False,
                    conditions={"max_value": 5000},
                ),
                Rule(
                    id="rule_manual_approve_high",
                    name="Manual approval for high value",
                    description="Require manual approval for orders above threshold",
                    policy_id="policy_high_value_approval",
                    tasks=[Task(name="book_shipment", tool_name="book_shipment")],
                    action="allow",
                    needs_approval=True,
                    conditions={"min_value": 5000},
                ),
            ],
        )
        self._policies[high_value_policy.id] = high_value_policy
    
    def _create_badge_internal(
        self,
        app_id: str,
        agent_url: str,
        capabilities: list[str],
    ) -> Badge:
        """Internal helper to create a badge."""
        credential = VerifiableCredential(
            issuer=f"did:agntcy:issuer:{uuid4().hex[:16]}",
            credential_subject=CredentialSubject(
                id=f"did:agntcy:agent:{app_id}",
                name=app_id,
                agent_url=agent_url,
                capabilities=capabilities,
            ),
            proof=Proof(
                type="Ed25519Signature2020",
                proof_purpose="assertionMethod",
                proof_value=f"mock_signature_{uuid4().hex}",
                verification_method=f"did:agntcy:issuer:key-1",
            ),
        )
        return Badge(app_id=app_id, verifiable_credential=credential)
    
    # ===========================
    # Application Management
    # ===========================
    
    async def get_all_apps(self) -> list[IdentityServiceApp]:
        """Get all registered applications."""
        return list(self._apps.values())
    
    async def get_app(self, app_id: str) -> IdentityServiceApp | None:
        """Get a specific application by ID."""
        return self._apps.get(app_id)
    
    async def register_app(
        self,
        name: str,
        description: str = "",
        app_type: str = "agent",
    ) -> IdentityServiceApp:
        """Register a new application."""
        app_id = f"{name.lower().replace(' ', '_')}_{uuid4().hex[:8]}"
        app = IdentityServiceApp(
            id=app_id,
            name=name,
            description=description,
            type=app_type,
            api_key=f"key_{uuid4().hex}",
            status="active",
        )
        self._apps[app_id] = app
        logger.info(f"Registered app: {app_id}")
        return app
    
    # ===========================
    # Badge Management
    # ===========================
    
    async def get_badge_for_app(self, app_id: str) -> Badge | None:
        """Get the badge for an application."""
        return self._badges.get(app_id)
    
    async def create_badge(
        self,
        agent_url: str,
        api_key: str,
        capabilities: list[str] | None = None,
    ) -> Badge:
        """Create a new badge."""
        # Find app by API key
        app = next(
            (a for a in self._apps.values() if a.api_key == api_key),
            None,
        )
        
        if not app:
            # Create new app
            app = await self.register_app(
                name=f"agent_{uuid4().hex[:8]}",
                description="Auto-registered agent",
            )
        
        badge = self._create_badge_internal(
            app_id=app.id,
            agent_url=agent_url,
            capabilities=capabilities or [],
        )
        self._badges[app.id] = badge
        logger.info(f"Created badge for: {app.id}")
        return badge
    
    async def verify_badge(self, badge: Badge) -> dict:
        """Verify a badge's authenticity."""
        # In local implementation, just check if badge exists
        stored_badge = self._badges.get(badge.app_id)
        
        if not stored_badge:
            return {"status": False, "error": "Badge not found"}
        
        # Check if credentials match
        if stored_badge.verifiable_credential.id != badge.verifiable_credential.id:
            return {"status": False, "error": "Credential mismatch"}
        
        return {"status": True}
    
    # ===========================
    # Policy Management
    # ===========================
    
    async def list_policies(self) -> list[Policy]:
        """List all policies."""
        return list(self._policies.values())
    
    async def get_policy(self, policy_id: str) -> Policy | None:
        """Get a specific policy."""
        return self._policies.get(policy_id)
    
    async def get_policies_for_app(self, app_id: str) -> list[Policy]:
        """Get policies assigned to an application."""
        return [p for p in self._policies.values() if p.assigned_to == app_id]
    
    async def check_permission(
        self,
        app_id: str,
        task_name: str,
        context: dict | None = None,
    ) -> dict:
        """Check if an application has permission to perform a task."""
        context = context or {}
        policies = await self.get_policies_for_app(app_id)
        
        for policy in policies:
            for rule in policy.rules:
                # Check if rule applies to this task
                task_match = any(t.name == task_name for t in rule.tasks)
                if not task_match:
                    continue
                
                # Check conditions
                conditions_met = True
                
                if "min_value" in rule.conditions:
                    order_value = context.get("order_value", 0)
                    if order_value < rule.conditions["min_value"]:
                        conditions_met = False
                
                if "max_value" in rule.conditions:
                    order_value = context.get("order_value", 0)
                    if order_value > rule.conditions["max_value"]:
                        conditions_met = False
                
                if conditions_met:
                    return {
                        "allowed": rule.action == "allow",
                        "needs_approval": rule.needs_approval,
                        "reason": rule.description,
                        "rule_id": rule.id,
                    }
        
        # Default: allow without approval if no matching policy
        return {
            "allowed": True,
            "needs_approval": False,
            "reason": "No matching policy found, defaulting to allow",
        }
    
    # ===========================
    # Approval Workflow
    # ===========================
    
    async def create_approval_request(
        self,
        task_type: str,
        resource_id: str,
        requester_did: str,
        amount: float | None = None,
        currency: str = "USD",
    ) -> ApprovalRequest:
        """Create a request for human approval."""
        request = ApprovalRequest(
            task_type=task_type,
            resource_id=resource_id,
            requester_did=requester_did,
            amount=amount,
            currency=currency,
            status="pending",
        )
        self._approval_requests[request.id] = request
        logger.info(f"Created approval request: {request.id}")
        return request
    
    async def get_approval_request(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        return self._approval_requests.get(request_id)
    
    async def approve_request(
        self,
        request_id: str,
        approver_did: str,
    ) -> ApprovalRequest:
        """Approve a pending request."""
        request = self._approval_requests.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")
        
        request.status = "approved"
        request.approved_at = datetime.utcnow()
        request.approver_did = approver_did
        
        logger.info(f"Approved request: {request_id} by {approver_did}")
        return request
    
    async def reject_request(
        self,
        request_id: str,
        approver_did: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """Reject a pending request."""
        request = self._approval_requests.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")
        
        request.status = "rejected"
        request.approved_at = datetime.utcnow()
        request.approver_did = approver_did
        
        logger.info(f"Rejected request: {request_id} by {approver_did}, reason: {reason}")
        return request
