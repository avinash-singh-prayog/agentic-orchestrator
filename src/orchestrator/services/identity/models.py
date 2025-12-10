"""
Identity Service Models

Pydantic models for identity-related data structures including
Badges, Verifiable Credentials, Policies, and Rules.

Based on the AGNTCY Identity Service specification from the
reference class diagram.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Proof(BaseModel):
    """Cryptographic proof attached to a verifiable credential."""
    
    type: str = Field(default="Ed25519Signature2020", description="Proof type")
    proof_purpose: str = Field(
        default="assertionMethod",
        alias="proofPurpose",
        description="Purpose of the proof",
    )
    proof_value: str = Field(
        default="",
        alias="proofValue",
        description="Base64-encoded signature",
    )
    created: datetime = Field(default_factory=datetime.utcnow)
    verification_method: str = Field(
        default="",
        alias="verificationMethod",
        description="DID verification method",
    )
    
    class Config:
        populate_by_name = True


class CredentialSubject(BaseModel):
    """Subject of a verifiable credential."""
    
    id: str = Field(..., description="DID of the credential subject")
    name: str = Field(default="", description="Human-readable name")
    agent_url: str = Field(
        default="",
        alias="agentUrl",
        description="URL of the agent",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of agent capabilities",
    )
    
    class Config:
        populate_by_name = True


class VerifiableCredential(BaseModel):
    """
    W3C Verifiable Credential for agent identity.
    
    Used to prove an agent's identity and capabilities
    in a cryptographically verifiable way.
    """
    
    context: list[str] = Field(
        default=["https://www.w3.org/2018/credentials/v1"],
        alias="@context",
        description="JSON-LD context",
    )
    type: list[str] = Field(
        default=["VerifiableCredential", "AgentBadge"],
        description="Credential types",
    )
    id: str = Field(
        default_factory=lambda: f"urn:uuid:{uuid4()}",
        description="Credential identifier",
    )
    issuer: str = Field(..., description="DID of the issuer")
    issuance_date: datetime = Field(
        default_factory=datetime.utcnow,
        alias="issuanceDate",
        description="When the credential was issued",
    )
    expiration_date: datetime | None = Field(
        default=None,
        alias="expirationDate",
        description="When the credential expires",
    )
    credential_subject: CredentialSubject = Field(
        ...,
        alias="credentialSubject",
        description="Subject of the credential",
    )
    proof: Proof | None = Field(default=None, description="Cryptographic proof")
    
    class Config:
        populate_by_name = True


class Badge(BaseModel):
    """
    Agent Badge containing a verifiable credential.
    
    Used for identity verification in the AGNTCY framework.
    """
    
    app_id: str = Field(alias="appId", description="Application/agent identifier")
    verifiable_credential: VerifiableCredential = Field(
        alias="verifiableCredential",
        description="The verifiable credential",
    )
    
    class Config:
        populate_by_name = True


class Task(BaseModel):
    """A task that an agent can perform."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Task name")
    description: str = Field(default="", description="Task description")
    tool_name: str = Field(
        default="",
        alias="toolName",
        description="Associated tool name",
    )
    
    class Config:
        populate_by_name = True


class Rule(BaseModel):
    """
    Access control rule within a policy.
    
    Defines what actions are allowed and whether approval is needed.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    policy_id: str = Field(alias="policyId", description="Parent policy ID")
    tasks: list[Task] = Field(default_factory=list, description="Allowed tasks")
    action: str = Field(default="allow", description="Action (allow/deny)")
    needs_approval: bool = Field(
        default=False,
        alias="needsApproval",
        description="Whether human approval is required",
    )
    conditions: dict[str, Any] = Field(
        default_factory=dict,
        description="Conditions for rule application",
    )
    
    class Config:
        populate_by_name = True


class Policy(BaseModel):
    """
    Task-Based Access Control (TBAC) Policy.
    
    Defines what an agent is allowed to do and under what conditions.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Policy name")
    description: str = Field(default="", description="Policy description")
    assigned_to: str = Field(
        alias="assignedTo",
        description="Agent/app ID this policy is assigned to",
    )
    rules: list[Rule] = Field(default_factory=list, description="Policy rules")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="updatedAt",
    )
    is_active: bool = Field(default=True, alias="isActive")
    
    class Config:
        populate_by_name = True


class IdentityServiceApp(BaseModel):
    """An application/agent registered with the identity service."""
    
    id: str = Field(..., description="Application identifier")
    name: str = Field(..., description="Application name")
    description: str = Field(default="", description="Application description")
    type: str = Field(default="agent", description="Application type")
    api_key: str = Field(
        default="",
        alias="apiKey",
        description="API key for authentication",
    )
    status: str = Field(default="active", description="Application status")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
    )
    
    class Config:
        populate_by_name = True


class ApprovalRequest(BaseModel):
    """Request for human approval of a task."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str = Field(alias="taskType", description="Type of task")
    resource_id: str = Field(alias="resourceId", description="Resource being acted upon")
    amount: float | None = Field(default=None, description="Amount (for financial approvals)")
    currency: str = Field(default="USD", description="Currency code")
    requester_did: str = Field(alias="requesterDid", description="DID of requester")
    status: str = Field(default="pending", description="Approval status")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
    )
    approved_at: datetime | None = Field(
        default=None,
        alias="approvedAt",
    )
    approver_did: str | None = Field(
        default=None,
        alias="approverDid",
    )
    
    class Config:
        populate_by_name = True
