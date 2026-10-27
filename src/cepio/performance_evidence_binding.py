"""Tenant-scoped host-bound evidence materialization for Performance Industry IQ.

Only host-owned plans select binding records. No user-provided evidence values, source
identifiers, tenant identity or formula definitions enter this boundary. Evidence
identity/version checks are NOT cryptographic source attestation or live readiness.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .application_contract import CEPIOApplicationService, ExecutionContext
from .model import ObjectRef
from .performance_industry_iq import PerformanceReasoningRequest
from .performance_runtime import PerformanceObservation
from .performance_service import PerformanceService
from .platform_bindings import (
    BindingCapability,
    BindingMode,
    BindingRegistration,
    BindingRuntimeStatus,
    EvidenceBinding,
    EvidenceEnvelope,
)


class BoundEvidenceError(ValueError):
    """No fallback to caller-supplied observations when source resolution fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class HostEvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    max_age_seconds: int = Field(gt=0)
    required: bool = True


class HostEvidencePlan(BaseModel):
    """Trusted host configuration; this model must never be a public request body."""

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(min_length=1)
    organization_id: str = Field(min_length=1)
    contract_id: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    subject: ObjectRef
    focus_node_id: str = Field(min_length=1)
    records: tuple[HostEvidenceRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_record_plan(self) -> "HostEvidencePlan":
        record_ids = [record.external_id for record in self.records]
        nodes = [record.node_id for record in self.records]
        if len(record_ids) != len(set(record_ids)) or len(nodes) != len(set(nodes)):
            raise ValueError("Host evidence records and performance node ids must be unique")
        if self.focus_node_id not in nodes:
            raise ValueError("Focus node requires an explicitly configured source record")
        if not any(item.node_id == self.focus_node_id and item.required for item in self.records):
            raise ValueError("Focus node evidence must be required")
        return self


class BoundEvidenceRequest(BaseModel):
    """Caller chooses only a registered host-owned plan and evaluation time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str = Field(min_length=1)
    evaluated_at: datetime
    simulation_only: Literal[True] = True


class BoundEvidencePayload(BaseModel):
    """Strict domain-neutral shape returned by the configured source binding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str
    subject_id: str
    node_id: str
    value: float = Field(allow_inf_nan=False)
    observed_at: datetime
    formula_ref: str | None = None


class BoundEvidenceSourceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    binding_id: str
    reference_key: str
    source_system: str
    record_version: str
    observed_at: datetime
    formula_ref: str | None = None


class BoundEvidenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    organization_id: str
    contract_id: str
    contract_version: str
    source_revision_hashes: tuple[str, ...]
    observations: tuple[PerformanceObservation, ...]
    source_records: tuple[BoundEvidenceSourceRecord, ...]
    reasoning_request: PerformanceReasoningRequest
    evidence_status: Literal["host_bound_source_not_attested"] = "host_bound_source_not_attested"
    authority: Literal["recommend_only"] = "recommend_only"
    policy_required: Literal[True] = True


class HostBoundPerformanceEvidenceService:
    """Prepare evidence for existing Performance Industry IQ without new reasoning."""

    def __init__(
        self,
        performance_service: PerformanceService,
        application_service: CEPIOApplicationService,
        binding: EvidenceBinding,
        registration: BindingRegistration,
        plans: tuple[HostEvidencePlan, ...],
    ) -> None:
        if registration.manifest != binding.manifest:
            raise BoundEvidenceError(
                "BINDING_IDENTITY_MISMATCH", "Registered manifest differs from source binding"
            )
        if binding.manifest.mode != BindingMode.evidence:
            raise BoundEvidenceError("READ_ONLY_BINDING_REQUIRED", "Evidence must be read-only")
        if not {
            BindingCapability.resolve_evidence,
            BindingCapability.versioned_identity,
        }.issubset(binding.manifest.capabilities):
            raise BoundEvidenceError(
                "VERSIONED_EVIDENCE_REQUIRED",
                "Evidence source must declare resolve-evidence and versioned-identity",
            )
        if hasattr(binding, "write_governed"):
            raise BoundEvidenceError(
                "READ_ONLY_BINDING_REQUIRED", "Evidence bindings cannot expose writes"
            )
        indexes = [plan.plan_id for plan in plans]
        if len(indexes) != len(set(indexes)):
            raise ValueError("Host evidence plan identities must be unique")
        self.performance_service = performance_service
        self.application_service = application_service
        self.binding = binding
        self.registration = registration
        self.plans = {item.plan_id: item for item in plans}

    def materialize(
        self,
        request: BoundEvidenceRequest,
        context: ExecutionContext,
    ) -> BoundEvidenceResult:
        if request.evaluated_at.tzinfo is None:
            raise BoundEvidenceError("TIMEZONE_REQUIRED", "Evaluation time must be timezone-aware")
        plan = self.plans.get(request.plan_id)
        if plan is None:
            raise BoundEvidenceError("PLAN_NOT_CONFIGURED", "Host evidence plan is not configured")
        # Enforce trusted tenant identity before reading contract, object or source.
        if context.tenant_id != plan.organization_id:
            raise BoundEvidenceError(
                "ORGANIZATION_SCOPE_MISMATCH", "Host evidence plan belongs to another tenant"
            )
        if self.registration.status != BindingRuntimeStatus.ready:
            raise BoundEvidenceError("BINDING_NOT_READY", "Source binding is not registered ready")
        resolution = self.performance_service.registry.resolve(
            plan.contract_id,
            plan.contract_version,
            organization_id=plan.organization_id,
        )
        contract = resolution.resolved.contract
        nodes = {node.id: node for node in contract.nodes}
        if plan.focus_node_id not in nodes:
            raise BoundEvidenceError("FOCUS_NODE_MISSING", "Focus node not in Performance Contract")

        obj = self.application_service.read_object(plan.subject.id, context)
        if obj.type != plan.subject.type:
            raise BoundEvidenceError("SUBJECT_TYPE_MISMATCH", "Source subject type differs")

        observations: list[PerformanceObservation] = []
        records: list[BoundEvidenceSourceRecord] = []
        for item in plan.records:
            node = nodes.get(item.node_id)
            if node is None:
                raise BoundEvidenceError("NODE_NOT_FOUND", "Configured KPI not in effective contract")
            try:
                envelope = self.binding.resolve_evidence(item.external_id)
            except KeyError as exc:
                if item.required:
                    raise BoundEvidenceError(
                        "REQUIRED_EVIDENCE_MISSING", "Required source record is missing"
                    ) from exc
                continue
            observed, source = self._validate_envelope(
                envelope, item, plan, node.formula_ref, request.evaluated_at
            )
            observations.append(observed)
            records.append(source)

        if not observations or not any(x.node_id == plan.focus_node_id for x in observations):
            raise BoundEvidenceError("FOCUS_EVIDENCE_MISSING", "No direct focus evidence")
        reasoning = PerformanceReasoningRequest(
            contract_id=plan.contract_id,
            contract_version=plan.contract_version,
            node_id=plan.focus_node_id,
            subject=plan.subject,
            observations=tuple(observations),
            evaluated_at=request.evaluated_at,
        )
        return BoundEvidenceResult(
            organization_id=plan.organization_id,
            contract_id=contract.id,
            contract_version=contract.version,
            source_revision_hashes=tuple(
                revision.definition_hash for revision in resolution.source_revisions
            ),
            observations=tuple(observations),
            source_records=tuple(records),
            reasoning_request=reasoning,
        )

    def _validate_envelope(
        self,
        envelope: EvidenceEnvelope,
        item: HostEvidenceRecord,
        plan: HostEvidencePlan,
        expected_formula: str | None,
        evaluated_at: datetime,
    ) -> tuple[PerformanceObservation, BoundEvidenceSourceRecord]:
        reference = envelope.reference
        if (
            reference.source_system != self.binding.manifest.source_system
            or reference.record_id != item.external_id
            or reference.record_kind != "performance-observation"
            or reference.record_version is None
            or str(reference.record_version).strip() == ""
        ):
            raise BoundEvidenceError(
                "SOURCE_PROVENANCE_MISMATCH",
                "Source record identity, kind or version does not match configured binding",
            )
        try:
            payload = BoundEvidencePayload.model_validate(envelope.evidence)
        except ValueError as exc:
            raise BoundEvidenceError("INVALID_SOURCE_PAYLOAD", "Source evidence is malformed") from exc
        if payload.organization_id != plan.organization_id or payload.subject_id != plan.subject.id:
            raise BoundEvidenceError(
                "SOURCE_SCOPE_MISMATCH", "Source record organization or subject differs"
            )
        if payload.node_id != item.node_id:
            raise BoundEvidenceError("SOURCE_NODE_MISMATCH", "Source record KPI identity differs")
        # Formula matching validates a declared convention, not whether the adapter
        # actually executed the formula or whether an external provider is authentic.
        if payload.formula_ref != expected_formula:
            raise BoundEvidenceError("FORMULA_MISMATCH", "Source formula reference differs")
        if payload.observed_at.tzinfo is None or payload.observed_at > evaluated_at:
            raise BoundEvidenceError(
                "SOURCE_TIME_INVALID", "Source time must be timezone-aware and not future-dated"
            )
        if (evaluated_at - payload.observed_at).total_seconds() > item.max_age_seconds:
            raise BoundEvidenceError("SOURCE_STALE", "Source evidence exceeds configured age")

        source = BoundEvidenceSourceRecord(
            node_id=item.node_id,
            binding_id=self.binding.manifest.binding_id,
            reference_key=reference.stable_key,
            source_system=reference.source_system,
            record_version=str(reference.record_version),
            observed_at=payload.observed_at,
            formula_ref=payload.formula_ref,
        )
        return (
            PerformanceObservation(
                node_id=item.node_id,
                value=payload.value,
                observed_at=payload.observed_at,
                source_subject_id=plan.subject.id,
                evidence_refs=(reference.stable_key,),
            ),
            source,
        )
