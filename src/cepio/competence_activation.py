"""Host-only, read-only IC-1 implicit competence activation reference gate.

This is candidate selection, NOT Skill dispatch, evidence attestation, diagnosis,
approval, or production qualification. The authorized host must supply scope,
asset identity and source-admitted evidence; untrusted prompts cannot assert them.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .capability_registry import (
    CapabilityMaturity,
    CapabilityRecord,
    CapabilityRegistry,
)
from .capability_routing import CapabilityRouter
from .retrieval_contracts import RetrievalIntent


class ActivationStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    BLOCKED = "BLOCKED"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"


class EvidenceState(str, Enum):
    HOST_ADMITTED = "HOST_ADMITTED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"


class ActivationScope(BaseModel):
    """Must be populated by an authorized host, never by the model/tool caller."""

    model_config = ConfigDict(extra="forbid")
    actor_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    permitted_asset_ids: set[str] = Field(default_factory=set)
    permitted_capability_ids: set[str] = Field(default_factory=set)
    permitted_evidence_refs: set[str] = Field(default_factory=set)


class ActivationTask(BaseModel):
    """Host-resolved equipment identity and task time, alongside user intent."""

    model_config = ConfigDict(extra="forbid")
    query_text: str = Field(min_length=3, max_length=2000)
    asset_id: str = Field(min_length=1, max_length=512)
    at: datetime

    @model_validator(mode="after")
    def require_aware_time(self) -> "ActivationTask":
        if self.at.tzinfo is None or self.at.utcoffset() is None:
            raise ValueError("activation time must be timezone-aware")
        if not self.query_text.strip():
            raise ValueError("activation requires a nonempty task")
        return self


class EvidenceAdmission(BaseModel):
    """Host-owned receipt, not a user assertion or independent source attestation."""

    model_config = ConfigDict(extra="forbid")
    requirement: str = Field(min_length=1, max_length=256)
    reference: str = Field(min_length=1, max_length=512)
    tenant_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    observed_at: datetime
    valid_until: datetime
    state: EvidenceState

    @model_validator(mode="after")
    def check_window(self) -> "EvidenceAdmission":
        for value in (self.observed_at, self.valid_until):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("evidence times must be timezone-aware")
        if self.valid_until <= self.observed_at:
            raise ValueError("evidence validity must end after observation")
        return self


class ActivationPolicy(BaseModel):
    """Lexical screening thresholds: not a calibrated engineering confidence."""

    model_config = ConfigDict(extra="forbid")
    minimum_route_score: float = Field(default=0.35, gt=0, le=1)
    ambiguity_margin: float = Field(default=0.05, ge=0, le=1)
    max_routed_capabilities: int = Field(default=50, ge=2, le=50)


class ActivationResult(BaseModel):
    status: ActivationStatus
    capability_id: str | None = None
    capability_version: str | None = None
    route_score: float | None = None
    reason_codes: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    admitted_evidence_refs: list[str] = Field(default_factory=list)


def _key(value: str) -> str:
    return value.strip().casefold()


def _candidate_registry(registry: CapabilityRegistry, scope: ActivationScope) -> CapabilityRegistry:
    return CapabilityRegistry(
        id=registry.id,
        version=registry.version,
        capabilities=[
            item for item in registry.capabilities
            if item.id in scope.permitted_capability_ids
            and item.maturity in {CapabilityMaturity.QUALIFIED, CapabilityMaturity.PRODUCTION}
        ],
    )


def _evidence_gates(
    capability: CapabilityRecord,
    scope: ActivationScope,
    task: ActivationTask,
    evidence: list[EvidenceAdmission],
) -> tuple[list[str], list[str], list[str]]:
    missing: list[str] = []
    admitted: set[str] = set()
    problems: set[str] = set()
    requirements = {_key(item): item for item in capability.evidence_requirements}

    if not requirements:
        return ["NO_EVIDENCE_REQUIREMENTS"], missing, []
    if not capability.evidence:
        problems.add("CAPABILITY_ASSURANCE_NOT_RECORDED")

    scoped = [
        item for item in evidence
        if item.tenant_id == scope.tenant_id
        and item.asset_id == task.asset_id
        and item.reference in scope.permitted_evidence_refs
    ]
    for normalized, label in sorted(requirements.items()):
        entries = [item for item in scoped if _key(item.requirement) == normalized]
        if not entries:
            missing.append(label)
            problems.add("REQUIRED_EVIDENCE_MISSING")
            continue
        # Duplicate source identities with inconsistent status or timestamps
        # cannot be made acceptable by placing a clean receipt beside them.
        by_ref: dict[str, tuple[EvidenceState, datetime, datetime]] = {}
        for item in entries:
            signature = (item.state, item.observed_at, item.valid_until)
            if item.reference in by_ref and by_ref[item.reference] != signature:
                problems.add("CONFLICTING_EVIDENCE")
            by_ref[item.reference] = signature

        if any(item.state == EvidenceState.CONFLICT for item in entries):
            problems.add("CONFLICTING_EVIDENCE")
        if any(item.state == EvidenceState.UNVERIFIED for item in entries):
            problems.add("UNVERIFIED_EVIDENCE")
        valid = [
            item for item in entries
            if item.state == EvidenceState.HOST_ADMITTED
            and item.observed_at <= task.at < item.valid_until
        ]
        if not valid:
            problems.add("STALE_OR_FUTURE_EVIDENCE")
        elif not any(
            item.state != EvidenceState.HOST_ADMITTED for item in entries
        ):
            admitted.update(item.reference for item in valid)

    return sorted(problems), sorted(missing), sorted(admitted)


def activate_competence(
    registry: CapabilityRegistry,
    *,
    task: ActivationTask,
    scope: ActivationScope,
    evidence: list[EvidenceAdmission],
    policy: ActivationPolicy | None = None,
) -> ActivationResult:
    """Route one industrial task into a governed review candidate, with no side effects.

    The scope and evidence must come from trusted host policy and provider
    verification; this method cannot authenticate or independently attest them.
    """
    rules = policy or ActivationPolicy()
    if task.asset_id not in scope.permitted_asset_ids or not scope.actor_id:
        return ActivationResult(status=ActivationStatus.BLOCKED, reason_codes=["ASSET_NOT_AUTHORIZED"])

    permitted = _candidate_registry(registry, scope)
    if not permitted.capabilities:
        return ActivationResult(status=ActivationStatus.NO_MATCH, reason_codes=["NO_ADMITTED_CAPABILITY"])

    intent = RetrievalIntent(
        query_text=task.query_text,
        tenant_id=scope.tenant_id,
        max_capabilities=rules.max_routed_capabilities,
        at=task.at,
    )
    routes = CapabilityRouter(permitted).route(intent).routes
    if not routes or routes[0].score < rules.minimum_route_score:
        return ActivationResult(status=ActivationStatus.NO_MATCH, reason_codes=["NO_SUITABLE_ROUTE"])
    if len(routes) > 1 and routes[0].score - routes[1].score <= rules.ambiguity_margin:
        return ActivationResult(
            status=ActivationStatus.AMBIGUOUS,
            reason_codes=["MULTIPLE_PLAUSIBLE_CAPABILITIES"],
        )

    best = routes[0]
    capability = permitted.get(best.capability_id)
    assert capability is not None  # only exact IDs from the filtered Registry
    blockers, missing, admitted = _evidence_gates(capability, scope, task, evidence)
    return ActivationResult(
        status=ActivationStatus.BLOCKED if blockers else ActivationStatus.CANDIDATE,
        capability_id=capability.id,
        capability_version=capability.version,
        route_score=best.score,
        reason_codes=blockers,
        missing_requirements=missing,
        admitted_evidence_refs=[] if blockers else admitted,
    )
