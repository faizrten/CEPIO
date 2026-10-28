"""Experimental host-owned Performance evidence handles and Decision receipts.

Synthetic/development assurance only. Source binding conformance is NOT external
source attestation. No public route, durable store, production release, authorization
to execute an Action or implicit Decision persistence is provided.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .application_contract import ExecutionContext
from .performance_evidence_binding import (
    BoundEvidenceRequest,
    BoundEvidenceResult,
    HostBoundPerformanceEvidenceService,
)
from .performance_executive import (
    ExecutivePackageRequest,
    ExecutivePerformancePackage,
    ExecutivePerformanceService,
)

Clock = Callable[[], datetime]


class AssuranceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class SourceVersionLock(BaseModel):
    """Host-controlled source expectation, not supplied by an agent/request body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(min_length=1)
    reference_key: str = Field(min_length=1)
    record_version: str = Field(min_length=1)


class AssurancePolicy(BaseModel):
    """Explicit, per-tenant host configuration for an offline assurance run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    organization_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    focus_node_id: str = Field(min_length=1)
    source_locks: tuple[SourceVersionLock, ...] = Field(min_length=1)
    allowed_roles: frozenset[str] = frozenset({"cepio_admin"})
    lifetime_seconds: int = Field(default=300, ge=1, le=900)
    max_current_clock_skew_seconds: int = Field(default=120, ge=0, le=600)


class EvidenceHandleRequest(BaseModel):
    """Caller can select a known host plan and mode, never evidence or source IDs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str = Field(min_length=1)
    evaluated_at: datetime
    mode: Literal["current", "historical_replay"] = "historical_replay"
    simulation_only: Literal[True] = True


class EvidenceHandle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    handle: str
    organization_id: str
    subject_id: str
    policy_id: str
    contract_version: str
    expires_at: datetime
    mode: Literal["current", "historical_replay"]
    evidence_trust: Literal["host_bound_not_source_attested"] = "host_bound_not_source_attested"


class DecisionAssuranceReceipt(BaseModel):
    """Recomputable integrity receipt, NOT a signature or authority to act."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.2.0"] = "0.2.0"
    handle: str
    organization_id: str
    subject_id: str
    actor_id: str
    evaluated_at: datetime
    policy_id: str
    policy_version: str
    mode: Literal["current", "historical_replay"]
    contract_id: str
    contract_version: str
    contract_source_hashes: tuple[str, ...]
    source_record_keys: tuple[str, ...]
    source_snapshot_sha256: str
    decision_package_sha256: str
    evidence_trust: Literal["host_bound_not_source_attested"] = "host_bound_not_source_attested"
    assurance_status: Literal["development_conformance_only"] = "development_conformance_only"
    authority: Literal["recommend_only"] = "recommend_only"
    policy_required: Literal[True] = True
    decision_persisted: Literal[False] = False
    workflow_started: Literal[False] = False
    action_executed: Literal[False] = False
    receipt_sha256: str


class AssuredExecutiveResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    package: ExecutivePerformancePackage
    receipt: DecisionAssuranceReceipt


@dataclass(frozen=True)
class _HandleEntry:
    actor_id: str
    organization_id: str
    bound: BoundEvidenceResult
    policy: AssurancePolicy
    expires_at: datetime
    mode: Literal["current", "historical_replay"]


def _sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AssuredPerformanceService:
    """Host-owned read-only bridge; handles never contain client KPI observations."""

    def __init__(
        self,
        evidence_service: HostBoundPerformanceEvidenceService,
        executive_service: ExecutivePerformanceService,
        policies: tuple[AssurancePolicy, ...],
        *,
        clock: Clock | None = None,
        max_handles: int = 1024,
    ) -> None:
        if not policies or max_handles < 1:
            raise ValueError("Host assurance policies and bounded handle capacity required")
        keys = [p.plan_id for p in policies]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate assurance plan identity")
        if any(
            len(p.source_locks) != len({lock.node_id for lock in p.source_locks})
            or not p.allowed_roles
            for p in policies
        ):
            raise ValueError("Source locks and roles must be unambiguous")
        self._evidence = evidence_service
        self._executive = executive_service
        self._policies = {p.plan_id: p for p in policies}
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._max_handles = max_handles
        self._entries: dict[str, _HandleEntry] = {}
        self._lock = threading.RLock()

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise AssuranceError(
                "TRUSTED_CLOCK_INVALID", "Trusted host clock must include timezone"
            )
        return now

    def issue(self, request: EvidenceHandleRequest, context: ExecutionContext) -> EvidenceHandle:
        policy = self._policies.get(request.plan_id)
        if policy is None:
            raise AssuranceError("PLAN_UNKNOWN", "Host plan is not configured")
        if context.tenant_id != policy.organization_id:
            raise AssuranceError("TENANT_DENIED", "Caller cannot access host plan")
        if not context.actor_id or not policy.allowed_roles.intersection(context.actor_roles):
            raise AssuranceError("ROLE_DENIED", "Caller lacks host assurance permission")
        now = self._now()
        if request.evaluated_at.tzinfo is None or request.evaluated_at > now:
            raise AssuranceError("EVALUATION_TIME_INVALID", "No naive or future evaluation times")
        if (
            request.mode == "current"
            and (now - request.evaluated_at).total_seconds() > policy.max_current_clock_skew_seconds
        ):
            raise AssuranceError(
                "CURRENT_EVIDENCE_STALE", "Current mode requires recent evaluation"
            )
        # Only the server-side configured materializer chooses source record IDs.
        bound = self._evidence.materialize(
            BoundEvidenceRequest(
                plan_id=policy.plan_id,
                evaluated_at=request.evaluated_at,
            ),
            context,
        )
        if (
            bound.organization_id != policy.organization_id
            or bound.reasoning_request.subject.id != policy.subject_id
            or bound.reasoning_request.node_id != policy.focus_node_id
            or bound.evidence_status != "host_bound_source_not_attested"
        ):
            raise AssuranceError("BOUND_RESULT_INVALID", "Bound source scope or identity changed")
        actual = {item.node_id: item for item in bound.source_records}
        for lock in policy.source_locks:
            item = actual.get(lock.node_id)
            if item is None:
                # Optional evidence may be absent; it remains unknown downstream.
                continue
            if (
                item.reference_key != lock.reference_key
                or item.record_version != lock.record_version
            ):
                raise AssuranceError("SOURCE_VERSION_CONFLICT", "Source identity/version drift")
        if set(actual) - {p.node_id for p in policy.source_locks}:
            raise AssuranceError("UNPINNED_SOURCE", "Unregistered source cannot become evidence")
        with self._lock:
            self._entries = {
                key: item for key, item in self._entries.items() if item.expires_at > now
            }
            if len(self._entries) >= self._max_handles:
                raise AssuranceError("HANDLE_CAPACITY", "Bounded handle capacity exceeded")
            handle = secrets.token_urlsafe(32)
            expires_at = now + timedelta(seconds=policy.lifetime_seconds)
            self._entries[handle] = _HandleEntry(
                actor_id=context.actor_id,
                organization_id=policy.organization_id,
                bound=bound,
                policy=policy,
                expires_at=expires_at,
                mode=request.mode,
            )
        return EvidenceHandle(
            handle=handle,
            organization_id=policy.organization_id,
            subject_id=policy.subject_id,
            policy_id=policy.policy_id,
            contract_version=bound.contract_version,
            expires_at=expires_at,
            mode=request.mode,
        )

    def preview(
        self, handle: str, context: ExecutionContext, *, financial_node_id: str | None = None
    ) -> AssuredExecutiveResult:
        with self._lock:
            entry = self._entries.get(handle)
        if entry is None:
            raise AssuranceError("HANDLE_UNKNOWN", "Evidence handle is unknown")
        if (
            context.tenant_id != entry.organization_id
            or context.actor_id != entry.actor_id
            or not entry.policy.allowed_roles.intersection(context.actor_roles)
        ):
            raise AssuranceError("HANDLE_ACCESS_DENIED", "Evidence handle belongs to another actor")
        if self._now() >= entry.expires_at:
            raise AssuranceError("HANDLE_EXPIRED", "Evidence handle has expired")
        # All observations are recovered from host state; never accept client data.
        package = self._executive.preview(
            ExecutivePackageRequest(
                reasoning=entry.bound.reasoning_request,
                financial_node_id=financial_node_id,
            ),
            context,
        )
        if (
            package.source_revision_hashes != entry.bound.source_revision_hashes
            or package.contract_id != entry.bound.contract_id
            or package.contract_version != entry.bound.contract_version
            or package.subject.id != entry.policy.subject_id
        ):
            raise AssuranceError("DECISION_PROVENANCE_DRIFT", "Executive output revision differs")
        if (
            package.authority != "recommend_only"
            or not package.policy_required
            or package.decision_persisted
            or package.workflow_started
            or package.action_executed
        ):
            raise AssuranceError("UNSAFE_EXECUTION_STATE", "Preview must never execute")
        keys = tuple(sorted(row.reference_key for row in entry.bound.source_records))
        receipt_data = {
            "handle": handle,
            "organization_id": entry.organization_id,
            "subject_id": entry.policy.subject_id,
            "actor_id": context.actor_id,
            "evaluated_at": entry.bound.reasoning_request.evaluated_at,
            "policy_id": entry.policy.policy_id,
            "policy_version": entry.policy.policy_version,
            "mode": entry.mode,
            "contract_id": entry.bound.contract_id,
            "contract_version": entry.bound.contract_version,
            "contract_source_hashes": entry.bound.source_revision_hashes,
            "source_record_keys": keys,
            "source_snapshot_sha256": _sha256(entry.bound.model_dump(mode="json")),
            "decision_package_sha256": _sha256(package.model_dump(mode="json")),
        }
        receipt = DecisionAssuranceReceipt.model_validate(
            {**receipt_data, "receipt_sha256": "0" * 64}
        )
        receipt = receipt.model_copy(
            update={
                "receipt_sha256": _sha256(
                    receipt.model_dump(mode="json", exclude={"receipt_sha256"})
                )
            }
        )
        return AssuredExecutiveResult(package=package, receipt=receipt)


def verify_assurance_receipt(receipt: DecisionAssuranceReceipt) -> bool:
    """Detect local receipt edits; this cannot authenticate an external issuer."""
    expected = _sha256(receipt.model_dump(mode="json", exclude={"receipt_sha256"}))
    return hmac.compare_digest(expected, receipt.receipt_sha256)
