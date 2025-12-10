"""Identity Service - Production-ready interface for agent identity and authorization."""

from orchestrator.services.identity.interface import IdentityService
from orchestrator.services.identity.local_impl import LocalIdentityService
from orchestrator.services.identity.models import (
    Badge,
    Policy,
    Proof,
    Rule,
    VerifiableCredential,
)

__all__ = [
    "IdentityService",
    "LocalIdentityService",
    "Badge",
    "Policy",
    "Proof",
    "Rule",
    "VerifiableCredential",
]
