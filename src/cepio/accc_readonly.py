"""Read-only ACCC composition candidate using existing CEPIO capability contracts.

This module does not execute Skills, query sources, infer missing evidence or authorize
Actions. Host-provided preflight/evidence results must come from trusted CEPIO services.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Literal

from .capability_registry import stable_hash

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .capability_registry import CapabilityMaturity, CapabilityRegistry
from .capability_routing import CapabilityRouter
from .retrieval_contracts import RetrievalIntent


class CompositionStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"


class CompositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query_text: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    subject_id: str | None = None
    required_capability_ids: set[str] = Field(default_factory=set)
    max_capabilities: int = Field(default=5, ge=1, le=20)


class TrustedAdmission(BaseModel):
    """Host-supplied, already-verified admission evidence; never agent-authored."""

    actor_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    approved_capability_ids: set[str] = Field(default_factory=set)
    ready_skill_ids: set[str] = Field(default_factory=set)
    verified_evidence_types: set[str] = Field(default_factory=set)
    incompatible_capability_ids: set[str] = Field(default_factory=set)
    source_conflicts: bool = False
    authorization_valid: bool = False
    receipt_context: dict[str, str] = Field(default_factory=dict)


class CompositionPlan(BaseModel):
    status: CompositionStatus
    capability_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    read_only: Literal[True] = True
    external_action_executed: Literal[False] = False
    manifest_hash: str | None = None
    receipt: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fail_closed(self) -> "CompositionPlan":
        if self.status != CompositionStatus.READY and (self.capability_ids or self.skill_ids):
            raise ValueError("non-ready plan cannot advertise admitted execution")
        if self.status == CompositionStatus.READY and (self.blockers or self.missing_evidence):
            raise ValueError("ready plan cannot have unresolved blockers")
        return self


class ReadOnlyComposer:
    """Deterministic admission baseline, not a model-assisted planner."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry
        self.router = CapabilityRouter(registry)

    def compose(self, request: CompositionRequest, admission: TrustedAdmission) -> CompositionPlan:
        if not admission.authorization_valid:
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["HOST_AUTHORIZATION_NOT_VERIFIED"]
            )
        routed = self.router.route(
            RetrievalIntent(
                query_text=request.query_text,
                tenant_id=admission.tenant_id,
                required_capability_ids=request.required_capability_ids,
                max_capabilities=request.max_capabilities,
            )
        )
        if routed.blocked:
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["REQUIRED_CAPABILITY_UNKNOWN"]
            )
        # An explicit required set is an allowlist for this bounded proof. Lexical
        # neighbors must never silently become admitted dependencies.
        candidate_routes = [
            route
            for route in routed.routes
            if not request.required_capability_ids
            or route.capability_id in request.required_capability_ids
        ]
        selected = []
        skills: set[str] = set()
        missing: set[str] = set()
        blockers: set[str] = set()
        for route in candidate_routes:
            capability = self.registry.get(route.capability_id)
            if capability is None:
                blockers.add("CAPABILITY_NOT_REGISTERED")
                continue
            if capability.layer.value == "PROFILE":
                blockers.add("PROFILE_CAPABILITY_NOT_SUPPORTED")
            if capability.id not in admission.approved_capability_ids:
                blockers.add("CAPABILITY_NOT_HOST_APPROVED")
            if capability.maturity not in {
                CapabilityMaturity.QUALIFIED,
                CapabilityMaturity.PRODUCTION,
            }:
                blockers.add("CAPABILITY_NOT_QUALIFIED")
            if request.domain not in capability.validated_domains:
                blockers.add("DOMAIN_NOT_VALIDATED")
            if capability.id in admission.incompatible_capability_ids:
                blockers.add("METHOD_INCOMPATIBLE")
            missing.update(capability.evidence_requirements - admission.verified_evidence_types)
            unready = capability.skills - admission.ready_skill_ids
            if unready:
                blockers.add("SKILL_PREFLIGHT_NOT_READY")
            selected.append(capability.id)
            skills.update(capability.skills)
        if request.required_capability_ids - set(selected):
            blockers.add("REQUIRED_CAPABILITY_NOT_SELECTED")
        if admission.source_conflicts:
            blockers.add("SOURCE_CONFLICT")
        if not selected:
            blockers.add("NO_ELIGIBLE_CAPABILITY")
        if blockers:
            return CompositionPlan(
                status=CompositionStatus.BLOCKED,
                blockers=sorted(blockers),
                missing_evidence=sorted(missing),
            )
        if missing:
            return CompositionPlan(
                status=CompositionStatus.NEEDS_EVIDENCE, missing_evidence=sorted(missing)
            )
        return CompositionPlan(
            status=CompositionStatus.READY,
            capability_ids=selected,
            skill_ids=sorted(skills),
            receipt=admission.receipt_context,
            manifest_hash=stable_hash(
                {
                    "capabilities": selected,
                    "skills": sorted(skills),
                    "registry_version": self.registry.version,
                    "domain": request.domain,
                    "subject_id": request.subject_id,
                    "query_text": request.query_text,
                    "capability_versions": {
                        item.id: item.version
                        for item in self.registry.capabilities
                        if item.id in selected
                    },
                    "host_receipt": admission.receipt_context,
                }
            ),
        )


class HostBoundComposer:
    """Trusted-host integration seam. Never register ReadOnlyComposer directly as an agent tool.

    The host must obtain the actor/tenant from authenticated session state and
    derive each admission fact from CEPIO runtime, preflight and source checks.
    The resolver must never deserialize an agent-provided TrustedAdmission.
    This wrapper is a boundary contract, NOT proof of an authenticated host.
    """

    def __init__(
        self,
        composer: ReadOnlyComposer,
        resolve_admission: Callable[[CompositionRequest], TrustedAdmission],
    ) -> None:
        self._composer = composer
        self._resolve_admission = resolve_admission

    def compose(self, request: CompositionRequest) -> CompositionPlan:
        try:
            admission = self._resolve_admission(request)
        except Exception:
            # A host outage must deny admission, not expose host internals.
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["HOST_ADMISSION_UNAVAILABLE"]
            )
        if not isinstance(admission, TrustedAdmission):
            return CompositionPlan(
                status=CompositionStatus.BLOCKED, blockers=["HOST_ADMISSION_UNAVAILABLE"]
            )
        return self._composer.compose(request, admission)
