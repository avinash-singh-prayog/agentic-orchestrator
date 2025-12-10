"""
Identity Service Interface

Abstract base class defining the contract for identity services.
This production-ready interface allows for pluggable implementations:
- LocalIdentityService (V1): In-memory implementation for development
- AGNTCYIdentityService (V2): Integration with AGNTCY Identity Service
"""

from abc import ABC, abstractmethod

from orchestrator.services.identity.models import (
    ApprovalRequest,
    Badge,
    IdentityServiceApp,
    Policy,
)


class IdentityService(ABC):
    """
    Abstract interface for identity and authorization services.
    
    Provides methods for:
    - Application/agent registration and discovery
    - Badge (Verifiable Credential) management
    - Policy-based access control
    - Approval workflow management
    
    Implementations:
    - LocalIdentityService: In-memory implementation for V1/development
    - AGNTCYIdentityService: Full AGNTCY integration (V2)
    """
    
    # ===========================
    # Application Management
    # ===========================
    
    @abstractmethod
    async def get_all_apps(self) -> list[IdentityServiceApp]:
        """
        Get all registered applications/agents.
        
        Returns:
            List of registered applications.
        """
        pass
    
    @abstractmethod
    async def get_app(self, app_id: str) -> IdentityServiceApp | None:
        """
        Get a specific application by ID.
        
        Args:
            app_id: Application identifier.
            
        Returns:
            Application if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def register_app(
        self,
        name: str,
        description: str = "",
        app_type: str = "agent",
    ) -> IdentityServiceApp:
        """
        Register a new application/agent.
        
        Args:
            name: Application name.
            description: Application description.
            app_type: Type of application.
            
        Returns:
            Newly registered application.
        """
        pass
    
    # ===========================
    # Badge Management
    # ===========================
    
    @abstractmethod
    async def get_badge_for_app(self, app_id: str) -> Badge | None:
        """
        Get the badge (verifiable credential) for an application.
        
        Args:
            app_id: Application identifier.
            
        Returns:
            Badge if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def create_badge(
        self,
        agent_url: str,
        api_key: str,
        capabilities: list[str] | None = None,
    ) -> Badge:
        """
        Create a new badge for an agent.
        
        Args:
            agent_url: URL of the agent.
            api_key: API key for authentication.
            capabilities: List of agent capabilities.
            
        Returns:
            Newly created badge.
        """
        pass
    
    @abstractmethod
    async def verify_badge(self, badge: Badge) -> dict:
        """
        Verify a badge's authenticity.
        
        Args:
            badge: Badge to verify.
            
        Returns:
            Verification result with 'status' and optional 'error'.
        """
        pass
    
    # ===========================
    # Policy Management
    # ===========================
    
    @abstractmethod
    async def list_policies(self) -> list[Policy]:
        """
        List all policies.
        
        Returns:
            List of policies.
        """
        pass
    
    @abstractmethod
    async def get_policy(self, policy_id: str) -> Policy | None:
        """
        Get a specific policy.
        
        Args:
            policy_id: Policy identifier.
            
        Returns:
            Policy if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def get_policies_for_app(self, app_id: str) -> list[Policy]:
        """
        Get all policies assigned to an application.
        
        Args:
            app_id: Application identifier.
            
        Returns:
            List of policies assigned to the application.
        """
        pass
    
    @abstractmethod
    async def check_permission(
        self,
        app_id: str,
        task_name: str,
        context: dict | None = None,
    ) -> dict:
        """
        Check if an application has permission to perform a task.
        
        Args:
            app_id: Application identifier.
            task_name: Name of the task to check.
            context: Optional context for conditional checks.
            
        Returns:
            Permission check result with 'allowed', 'needs_approval', and 'reason'.
        """
        pass
    
    # ===========================
    # Approval Workflow
    # ===========================
    
    @abstractmethod
    async def create_approval_request(
        self,
        task_type: str,
        resource_id: str,
        requester_did: str,
        amount: float | None = None,
        currency: str = "USD",
    ) -> ApprovalRequest:
        """
        Create a request for human approval.
        
        Args:
            task_type: Type of task requiring approval.
            resource_id: Resource being acted upon.
            requester_did: DID of the requester.
            amount: Amount for financial approvals.
            currency: Currency code.
            
        Returns:
            Created approval request.
        """
        pass
    
    @abstractmethod
    async def get_approval_request(self, request_id: str) -> ApprovalRequest | None:
        """
        Get an approval request by ID.
        
        Args:
            request_id: Request identifier.
            
        Returns:
            Approval request if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def approve_request(
        self,
        request_id: str,
        approver_did: str,
    ) -> ApprovalRequest:
        """
        Approve a pending request.
        
        Args:
            request_id: Request identifier.
            approver_did: DID of the approver.
            
        Returns:
            Updated approval request.
        """
        pass
    
    @abstractmethod
    async def reject_request(
        self,
        request_id: str,
        approver_did: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """
        Reject a pending request.
        
        Args:
            request_id: Request identifier.
            approver_did: DID of the approver.
            reason: Rejection reason.
            
        Returns:
            Updated approval request.
        """
        pass
