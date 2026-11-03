"""Host-only, request-scoped ACCC binding. No public endpoint or execution surface.

The principal callback must invoke existing host authentication on EVERY call.
Evidence adapters remain trusted host code, not cryptographic source attestation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .accc_readonly import (
    CompositionPlan,
    CompositionRequest,
    CompositionStatus,
    ReadOnlyComposer,
    TrustedAdmission,
)
from .auth import ActorContext, get_actor_context
from .capability_registry import CapabilityRegistry, stable_hash
from .platform_bindings import (
    BindingCapability,
    BindingMode,
    BindingRegistration,
    BindingRuntimeStatus,
    EvidenceBinding,
)
from .skill_preflight import SkillRegistry


def contract_hash(value: BaseModel) -> str:
    """Hash set-valued contracts deterministically across Python processes."""

    def canonical(item):
        if isinstance(item, dict):
            return {key: canonical(val) for key, val in item.items()}
        if isinstance(item, (set, frozenset)):
            return sorted(canonical(val) for val in item)
        if isinstance(item, (tuple, list)):
            return [canonical(val) for val in item]
        return item

    return stable_hash(canonical(value.model_dump(mode="python")))


@dataclass(frozen=True)
class EvidenceRequirement:
    external_id: str
    evidence_type: str
    max_age_seconds: int


@dataclass(frozen=True)
class AdmissionProfile:
    """Host configuration, never deserialized from a tool request.

    Exact contract digests pin qualified Skills and compatible methods. Unsupported
    policy requirements fail closed instead of inventing an interpretation.
    """

    tenant_id: str
    subject_id: str
    domain: str
    policy_version: str
    capability_hashes: dict[str, str]
    skill_hashes: dict[str, str]
    compatible_sets: frozenset[frozenset[str]]
    evidence: tuple[EvidenceRequirement, ...]


class EvidenceState(BaseModel):
    """Adapter payload convention; not a canonical industrial ontology concept."""

    model_config = ConfigDict(extra="forbid")
    tenant_id: str
    subject_id: str
    evidence_type: str
    observed_at: datetime
    conflict: bool
    # Interpretation stays in the source adapter/Industry IQ.
    payload_hash: str = Field(min_length=1)


class AuthenticatedReadOnlyComposer:
    """Re-check authentication, policy, source scope and preflight for every request."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        skills: SkillRegistry,
        authenticate: Callable[[], ActorContext],
        binding: EvidenceBinding,
        registration: BindingRegistration,
        profile: AdmissionProfile,
        clock: Callable[[], datetime],
    ) -> None:
        self.registry = registry
        self.skills = skills
        self.authenticate = authenticate
        self.binding = binding
        self.registration = registration
        self.profile = profile
        self.clock = clock

    @classmethod
    def from_http_request(cls, *, http_request, credentials, **host_configuration):
        """Use existing CEPIO authentication unchanged; no new route is registered.

        Construct per request. Credentials and request are never tool arguments.
        Existing host settings decide validation mode; production settings stay
        unchanged. Token validation is repeated for each composition.
        """
        return cls(
            authenticate=lambda: get_actor_context(http_request, credentials),
            **host_configuration,
        )

    def compose(self, request: CompositionRequest) -> CompositionPlan:
        try:
            return self._compose(request)
        except Exception:
            # No backend exception, evidence, identity or credential leaks to tools.
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["HOST_ADMISSION_UNAVAILABLE"]
            )

    def _compose(self, request: CompositionRequest) -> CompositionPlan:
        actor = self.authenticate()
        profile = self.profile
        if (
            not isinstance(actor, ActorContext)
            or not actor.actor_id
            or not actor.roles
            or actor.tenant_id != profile.tenant_id
            or not profile.tenant_id
            or not profile.policy_version
            or request.subject_id != profile.subject_id
            or request.domain != profile.domain
        ):
            raise PermissionError("host scope mismatch")
        runtime = self.skills.runtime
        if not runtime.policy_engine.can_call_function(actor.roles, "cepio.compose_readonly"):
            raise PermissionError("composition permission revoked")
        target = runtime.get_object(profile.subject_id)
        # Include object sharing policy, which type-level authorization alone omits.
        if not runtime.policy_engine.can_read_object(actor.roles, target):
            raise PermissionError("subject not authorized")
        runtime.read_object_for_actor(target.id, actor.roles)
        manifest = self.binding.manifest
        if (
            manifest != self.registration.manifest
            or self.registration.status != BindingRuntimeStatus.ready
            or manifest.mode != BindingMode.evidence
            or BindingCapability.versioned_identity not in manifest.capabilities
            or hasattr(self.binding, "write_governed")
        ):
            raise PermissionError("read-only versioned binding required")
        required = request.required_capability_ids
        if not required or frozenset(required) not in profile.compatible_sets:
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["METHOD_INCOMPATIBLE"]
            )
        approved, ready = set(), set()
        required_skills: set[str] = set()
        receipts = {"policy_version": profile.policy_version, "tenant_id": actor.tenant_id}
        receipts["actor"] = stable_hash([actor.actor_id, sorted(actor.roles)])
        for capability_id in sorted(required):
            capability = self.registry.get(capability_id)
            if capability is None:
                continue
            if (
                contract_hash(capability) != profile.capability_hashes.get(capability_id)
                or capability.policy_requirements
                or not capability.authority_requirements.issubset(actor.roles)
            ):
                continue
            approved.add(capability_id)
            required_skills.update(capability.skills)
            receipts["capability:" + capability_id] = contract_hash(capability)
            for skill_id in sorted(capability.skills):
                spec = self.skills.get(skill_id)
                # No Action-bearing or Decision-producing Skill enters this surface.
                if (
                    spec.actions
                    or spec.authority.execute_actions
                    or spec.authority.propose_decision
                    or spec.decisions
                    or contract_hash(spec) != profile.skill_hashes.get(skill_id)
                ):
                    continue
                result = self.skills.preflight(
                    skill_id, actor_id=actor.actor_id, actor_roles=set(actor.roles)
                )
                if result.status == "READY":
                    ready.add(skill_id)
                    receipts["skill:" + skill_id] = contract_hash(spec)
        # Deny unqualified capabilities/Skills before contacting the source.
        if approved != required or not required_skills.issubset(ready):
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["CAPABILITY_OR_SKILL_NOT_ADMITTED"]
            )
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("host time must be timezone aware")
        verified = set()
        unavailable = set()
        conflicts = False
        for item in profile.evidence:
            if item.max_age_seconds <= 0:
                raise ValueError("invalid freshness bound")
            if not runtime.policy_engine.can_read_type(actor.roles, item.evidence_type):
                raise PermissionError("evidence type not authorized")
            try:
                envelope = self.binding.resolve_evidence(item.external_id)
            except KeyError:
                unavailable.add(item.evidence_type)
                continue
            reference = envelope.reference
            state = EvidenceState.model_validate(envelope.evidence)
            if (
                reference.source_system != manifest.source_system
                or reference.record_id != item.external_id
                or reference.record_kind != item.evidence_type
                or not str(reference.record_version or "").strip()
                or state.tenant_id != actor.tenant_id
                or state.subject_id != target.id
                or state.evidence_type != item.evidence_type
                or state.observed_at.tzinfo is None
                or state.observed_at > now
            ):
                raise PermissionError("source scope/provenance mismatch")
            conflicts |= state.conflict
            if (now - state.observed_at).total_seconds() > item.max_age_seconds:
                unavailable.add(item.evidence_type)
                continue
            verified.add(item.evidence_type)
            receipts["evidence:" + item.external_id] = contract_hash(envelope)
        receipts["evaluated_at"] = now.isoformat()
        receipts["binding"] = contract_hash(self.registration)
        return ReadOnlyComposer(self.registry).compose(
            request,
            TrustedAdmission(
                actor_id=actor.actor_id,
                tenant_id=actor.tenant_id,
                authorization_valid=True,
                approved_capability_ids=approved,
                ready_skill_ids=ready,
                verified_evidence_types=verified - unavailable,
                source_conflicts=conflicts,
                receipt_context=receipts,
            ),
        )
