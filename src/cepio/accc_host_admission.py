"""Host-only ACCC admission adapter.

This adapter is not an authentication provider. Its inputs must originate in
an authenticated CEPIO host; do not expose them as agent tool arguments.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from .accc_readonly import CompositionRequest, TrustedAdmission
from .capability_registry import CapabilityRegistry
from .skill_preflight import SkillRegistry


@dataclass(frozen=True)
class HostPrincipal:
    actor_id: str
    tenant_id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class EvidenceVerification:
    verified: bool
    evidence_types: frozenset[str]
    conflicts: bool = False


class HostAdmissionServices(Protocol):
    def authenticated_principal(self) -> HostPrincipal: ...
    def verify_evidence(
        self, request: CompositionRequest, principal: HostPrincipal
    ) -> EvidenceVerification: ...
    def eligible_capabilities(
        self, request: CompositionRequest, principal: HostPrincipal
    ) -> set[str]: ...
    def incompatible_capabilities(
        self, request: CompositionRequest, principal: HostPrincipal
    ) -> set[str]: ...


class RuntimeAdmissionResolver:
    """Resolve admission from host-owned identity, evidence and real preflight."""

    def __init__(
        self, registry: CapabilityRegistry, skills: SkillRegistry, services: HostAdmissionServices
    ):
        self.registry = registry
        self.skills = skills
        self.services = services

    def __call__(self, request: CompositionRequest) -> TrustedAdmission:
        principal = self.services.authenticated_principal()
        if not isinstance(principal, HostPrincipal) or not all(
            (principal.actor_id, principal.tenant_id, principal.roles)
        ):
            raise PermissionError("host principal unavailable")
        evidence = self.services.verify_evidence(request, principal)
        if not isinstance(evidence, EvidenceVerification) or not evidence.verified:
            raise PermissionError("source evidence not verified")
        approved = self.services.eligible_capabilities(request, principal)
        incompatible = self.services.incompatible_capabilities(request, principal)
        if not isinstance(approved, set) or not isinstance(incompatible, set):
            raise PermissionError("capability eligibility unavailable")
        ready: set[str] = set()
        for capability in self.registry.capabilities:
            if capability.id not in approved:
                continue
            for skill_id in capability.skills:
                try:
                    result = self.skills.preflight(
                        skill_id,
                        actor_id=principal.actor_id,
                        actor_roles=set(principal.roles),
                    )
                except (KeyError, ValueError, PermissionError):
                    continue
                if result.status == "READY":
                    ready.add(skill_id)
        return TrustedAdmission(
            actor_id=principal.actor_id,
            tenant_id=principal.tenant_id,
            approved_capability_ids=approved,
            ready_skill_ids=ready,
            verified_evidence_types=set(evidence.evidence_types),
            incompatible_capability_ids=incompatible,
            source_conflicts=evidence.conflicts,
            authorization_valid=True,
        )
