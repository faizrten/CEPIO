"""Host-scoped, read-only operational state and evidence reference inspection.

Composes existing CEPIO temporal object history, Application Contract and versioned
Evidence Binding. It does not infer plant state from raw evidence or attest a source.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .application_contract import CEPIOApplicationService, ExecutionContext
from .model import ObjectRef, OntologyObject
from .operational_object_inspection import (
    OperationalObjectInspection,
    inspect_operational_object,
)
from .platform_bindings import (
    BindingCapability,
    BindingMode,
    BindingRegistration,
    BindingRuntimeStatus,
    EvidenceBinding,
)


class OperationalStateReadError(ValueError):
    """Fail-closed read error with a stable, non-source-specific code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class HostOperationalStatePlan(BaseModel):
    """Host-owned source/tenant selection; never accept as a caller-authored request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str = Field(min_length=1)
    organization_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    subject: ObjectRef
    external_id: str = Field(min_length=1)
    record_kind: str = Field(min_length=1)
    max_age_seconds: int = Field(gt=0)


class SourceObservationMetadata(BaseModel):
    """Only the metadata needed for provenance/freshness checks; no source payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str
    subject_id: str
    observed_at: datetime


class VersionedObservationReceipt(BaseModel):
    """Verified reference consistency, not cryptographic authenticity or plant truth."""

    model_config = ConfigDict(frozen=True)

    binding_id: str
    source_system: str
    record_kind: str
    record_id: str
    record_version: str
    observed_at: datetime
    age_seconds: float
    freshness: Literal["within_configured_window"] = "within_configured_window"
    authenticity: Literal["not_attested"] = "not_attested"


class OperationalStateInspection(BaseModel):
    """Read-only state view; no assertion that source record proves the state value."""

    model_config = ConfigDict(frozen=True)

    object_inspection: OperationalObjectInspection
    historical_subject: OntologyObject
    valid_at: datetime
    evaluated_at: datetime
    receipt: VersionedObservationReceipt
    source_to_state_alignment: Literal["not_proven"] = "not_proven"
    action_authority: Literal["not_evaluated"] = "not_evaluated"


def inspect_operational_state(
    service: CEPIOApplicationService,
    binding: EvidenceBinding,
    registration: BindingRegistration,
    plan: HostOperationalStatePlan,
    context: ExecutionContext,
    *,
    valid_at: datetime,
    evaluated_at: datetime,
    max_related: int = 25,
) -> OperationalStateInspection:
    """Inspect a tenant-bound temporal object and one versioned source record.

    A ready binding, matching source reference, and freshness window are necessary
    consistency checks, but are not proof of source authenticity, data-field
    reconciliation, causality, current plant condition or production qualification.
    """
    if valid_at.tzinfo is None or evaluated_at.tzinfo is None:
        raise OperationalStateReadError("TIMEZONE_REQUIRED", "Query times must be timezone-aware")
    if valid_at > evaluated_at:
        raise OperationalStateReadError("TIME_INVALID", "Valid time cannot follow evaluation time")
    if context.tenant_id is None or context.tenant_id != plan.organization_id:
        raise OperationalStateReadError("TENANT_DENIED", "Host tenant does not match the plan")
    if (
        registration.manifest != binding.manifest
        or registration.capability_id != plan.capability_id
    ):
        raise OperationalStateReadError("BINDING_MISMATCH", "Configured binding contract differs")
    if registration.status != BindingRuntimeStatus.ready:
        raise OperationalStateReadError("BINDING_NOT_READY", "Configured binding is not ready")
    if (
        binding.manifest.mode != BindingMode.evidence
        or hasattr(binding, "write_governed")
        or not {
            BindingCapability.resolve_evidence,
            BindingCapability.versioned_identity,
        }.issubset(binding.manifest.capabilities)
    ):
        raise OperationalStateReadError(
            "READ_ONLY_VERSIONED_REQUIRED", "Read-only versioned binding required"
        )

    # Authorize the object before touching the external source.
    inspection = inspect_operational_object(
        service, plan.subject.id, context, max_related=max_related
    )
    current = inspection.context.subject
    if current.type != plan.subject.type:
        raise OperationalStateReadError("SUBJECT_TYPE_MISMATCH", "Subject type differs")

    # The current read grant is not sufficient to expose a historical snapshot:
    # enforce policy again on the historical object's scope/properties.
    temporal_reader = getattr(service.runtime, "get_object_valid_at", None)
    if not callable(temporal_reader):
        raise OperationalStateReadError("HISTORY_UNAVAILABLE", "Temporal object reads unavailable")
    try:
        historical = temporal_reader(plan.subject.id, valid_at)
    except KeyError as exc:
        raise OperationalStateReadError(
            "HISTORY_MISSING", "No object state valid at requested time"
        ) from exc
    if historical.id != current.id or historical.type != current.type:
        raise OperationalStateReadError(
            "HISTORY_IDENTITY_MISMATCH", "Temporal object identity differs"
        )
    roles = set(context.actor_roles)
    policy = service.runtime.policy_engine
    if not policy.can_read_object(roles, historical):
        raise OperationalStateReadError("HISTORY_DENIED", "Historical object is not accessible")
    historical_visible = policy.filter_properties(roles, historical)

    # Source resolution is deliberately after all object and tenant authorization.
    try:
        envelope = binding.resolve_evidence(plan.external_id)
    except KeyError as exc:
        raise OperationalStateReadError(
            "SOURCE_MISSING", "Configured source record is missing"
        ) from exc
    reference = envelope.reference
    if (
        reference.source_system != binding.manifest.source_system
        or reference.record_id != plan.external_id
        or reference.record_kind != plan.record_kind
        or reference.record_version is None
        or not str(reference.record_version).strip()
    ):
        raise OperationalStateReadError(
            "SOURCE_IDENTITY_MISMATCH", "Source record identity/version differs"
        )
    try:
        metadata = SourceObservationMetadata.model_validate(envelope.evidence)
    except ValueError as exc:
        raise OperationalStateReadError(
            "SOURCE_METADATA_INVALID", "Source observation metadata invalid"
        ) from exc
    if metadata.organization_id != plan.organization_id or metadata.subject_id != current.id:
        raise OperationalStateReadError("SOURCE_SCOPE_MISMATCH", "Source observation scope differs")
    if metadata.observed_at.tzinfo is None or metadata.observed_at > valid_at:
        raise OperationalStateReadError(
            "SOURCE_TIME_INVALID", "Source time invalid for requested state"
        )
    age_seconds = (valid_at - metadata.observed_at).total_seconds()
    if age_seconds > plan.max_age_seconds:
        raise OperationalStateReadError(
            "SOURCE_STALE", "Source observation is outside configured age window"
        )

    return OperationalStateInspection(
        object_inspection=inspection,
        historical_subject=historical_visible,
        valid_at=valid_at,
        evaluated_at=evaluated_at,
        receipt=VersionedObservationReceipt(
            binding_id=registration.manifest.binding_id,
            source_system=reference.source_system,
            record_kind=reference.record_kind,
            record_id=reference.record_id,
            record_version=str(reference.record_version),
            observed_at=metadata.observed_at,
            age_seconds=age_seconds,
        ),
    )
