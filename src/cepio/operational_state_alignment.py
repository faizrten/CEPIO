"""Read-only state-claim alignment over existing CEPIO object and evidence contracts.

A consistent claim is NOT verified operating state. Only a trusted host can supply
the mapping plan and binding selections. This module never mutates an object,
persists a Decision, dispatches an Action, or trusts source values as authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .application_contract import CEPIOApplicationService, ExecutionContext
from .model import ObjectRef, OntologyObject
from .operational_state_inspection import (
    HostOperationalStatePlan,
    OperationalStateInspection,
    VersionedObservationReceipt,
    inspect_operational_state,
)
from .platform_bindings import (
    BindingRegistration,
    EvidenceBinding,
    EvidenceEnvelope,
    PlatformBindingManifest,
)
from .property_registry import UnknownPropertyError


class StateAlignmentError(ValueError):
    """Stable fail-closed error. Messages exclude raw source values and identities."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class HostStateAlignmentPlan(BaseModel):
    """Trusted host configuration, not a REST/MCP request payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str = Field(min_length=1)
    subject: ObjectRef
    property_iri: str = Field(min_length=1)
    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    allowed_values: tuple[str, ...] = Field(min_length=1)


class NormalizedStateEvidence(BaseModel):
    """Adapter-normalized claim; strict shape limits accidental source-data copying."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    observed_at: datetime
    property_iri: str = Field(min_length=1)
    state_value: str = Field(min_length=1)
    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)


@dataclass(frozen=True)
class StateSourceSelection:
    """Host-owned registration and role; the provider cannot nominate itself primary."""

    binding: EvidenceBinding
    registration: BindingRegistration
    plan: HostOperationalStatePlan
    role: Literal["primary", "corroborating"]


class _MetadataOnlyBinding:
    """Capture a single source envelope while reusing M2's exact safety checks."""

    def __init__(self, binding: EvidenceBinding) -> None:
        self.delegate = binding
        self.manifest: PlatformBindingManifest = binding.manifest
        self.claim: NormalizedStateEvidence | None = None

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        source = self.delegate.resolve_evidence(external_id)
        try:
            claim = NormalizedStateEvidence.model_validate(source.evidence)
        except ValueError as exc:
            raise StateAlignmentError(
                "SOURCE_STATE_INVALID", "Normalized source claim is malformed"
            ) from exc
        self.claim = claim
        return EvidenceEnvelope(
            reference=source.reference,
            evidence={
                "organization_id": claim.organization_id,
                "subject_id": claim.subject_id,
                "observed_at": claim.observed_at,
            },
        )


class OperationalStateAlignment(BaseModel):
    """An evidence-consistency assessment with no production authority."""

    model_config = ConfigDict(frozen=True)

    status: Literal[
        "consistent_candidate",
        "conflict_blocked",
        "historical_mismatch",
        "insufficient_independent_sources",
    ]
    subject: ObjectRef
    property_iri: str
    historical_subject: OntologyObject
    evaluated_at: datetime
    valid_at: datetime
    agreed_value: str | None
    observations: tuple[VersionedObservationReceipt, ...]
    source_authenticity: Literal["not_attested"] = "not_attested"
    state_authority: Literal["not_qualified"] = "not_qualified"
    decision_eligible: Literal[False] = False


def assess_operational_state_alignment(
    service: CEPIOApplicationService,
    mapping: HostStateAlignmentPlan,
    sources: tuple[StateSourceSelection, ...],
    context: ExecutionContext,
    *,
    valid_at: datetime,
    evaluated_at: datetime,
) -> OperationalStateAlignment:
    """Compare bounded versioned claims without rewriting source or CEPIO state.

    M2 authenticates neither external providers nor mapping semantics. A matching
    candidate remains non-authoritative until source ownership, identity, timestamp
    and field-to-state mapping receive separate independent qualification.
    """
    if context.tenant_id is None or context.tenant_id != mapping.organization_id:
        raise StateAlignmentError("TENANT_DENIED", "Host organization scope differs")
    if not 1 <= len(sources) <= 4:
        raise StateAlignmentError("SOURCE_COUNT_INVALID", "One to four source bindings required")
    if sum(source.role == "primary" for source in sources) != 1:
        raise StateAlignmentError("PRIMARY_REQUIRED", "Exactly one host-nominated primary is required")
    if any(source.role not in {"primary", "corroborating"} for source in sources):
        raise StateAlignmentError("SOURCE_ROLE_INVALID", "Unsupported source role")
    if not all(value.strip() for value in mapping.allowed_values):
        raise StateAlignmentError("ALLOWED_VALUES_INVALID", "Host state vocabulary contains blank values")

    keys = [
        (source.registration.manifest.binding_id, source.plan.external_id)
        for source in sources
    ]
    if len(keys) != len(set(keys)):
        raise StateAlignmentError("DUPLICATE_SOURCE", "Repeated source reference is not independent")
    if any(
        item.plan.organization_id != mapping.organization_id
        or item.plan.subject != mapping.subject
        for item in sources
    ):
        raise StateAlignmentError("PLAN_SCOPE_MISMATCH", "State source plan differs from host scope")

    registry = getattr(service.runtime, "property_registry", None)
    if registry is None:
        raise StateAlignmentError("PROPERTY_REGISTRY_REQUIRED", "Canonical property registry required")
    try:
        property_definition = registry.resolve(mapping.property_iri)
    except (UnknownPropertyError, ValueError) as exc:
        raise StateAlignmentError("PROPERTY_UNDECLARED", "State property is not canonical") from exc
    if property_definition.iri != mapping.property_iri or property_definition.datatype != "string":
        raise StateAlignmentError("PROPERTY_UNSUPPORTED", "State mapping requires a canonical string IRI")

    # Fail closed before any binding lookup if the caller lacks *current* property
    # visibility. M2 then separately authorizes the historical property's scope.
    subject = service.read_object(mapping.subject.id, context)
    if subject.type != mapping.subject.type:
        raise StateAlignmentError("SUBJECT_TYPE_MISMATCH", "Object type differs")
    if mapping.property_iri not in subject.properties:
        raise StateAlignmentError("STATE_PROPERTY_NOT_VISIBLE", "State property is not visible")

    views: list[OperationalStateInspection] = []
    values: list[str] = []
    for selection in sources:
        if hasattr(selection.binding, "write_governed"):
            raise StateAlignmentError("READ_ONLY_REQUIRED", "State sources must not expose write")
        captured = _MetadataOnlyBinding(selection.binding)
        view = inspect_operational_state(
            service,
            captured,
            selection.registration,
            selection.plan,
            context,
            valid_at=valid_at,
            evaluated_at=evaluated_at,
            max_related=1,
        )
        claim = captured.claim
        if claim is None:
            raise StateAlignmentError("CLAIM_MISSING", "Source did not return a normalized claim")
        if (
            claim.property_iri != mapping.property_iri
            or claim.mapping_id != mapping.mapping_id
            or claim.mapping_version != mapping.mapping_version
            or claim.organization_id != mapping.organization_id
            or claim.subject_id != mapping.subject.id
        ):
            raise StateAlignmentError("MAPPING_MISMATCH", "Source mapping contract differs")
        if claim.state_value not in mapping.allowed_values:
            raise StateAlignmentError("STATE_VALUE_UNSUPPORTED", "State value is outside host vocabulary")
        if mapping.property_iri not in view.historical_subject.properties:
            raise StateAlignmentError("HISTORICAL_PROPERTY_DENIED", "Historical property is not visible")
        if views and (
            view.historical_subject != views[0].historical_subject
            or view.valid_at != views[0].valid_at
            or view.evaluated_at != views[0].evaluated_at
        ):
            raise StateAlignmentError("SNAPSHOT_MISMATCH", "Source inspections use different snapshots")
        views.append(view)
        values.append(claim.state_value)

    historical = views[0].historical_subject
    historical_value = historical.properties[mapping.property_iri]
    if not isinstance(historical_value, str):
        raise StateAlignmentError("HISTORICAL_VALUE_UNSUPPORTED", "Historical state is not a string")
    distinct = set(values)
    independent = {view.receipt.source_system for view in views}
    if len(distinct) > 1:
        status = "conflict_blocked"
        agreed = None
    elif historical_value not in distinct:
        status = "historical_mismatch"
        agreed = None
    elif len(independent) < 2:
        status = "insufficient_independent_sources"
        agreed = None
    else:
        status = "consistent_candidate"
        agreed = values[0]

    return OperationalStateAlignment(
        status=status,
        subject=mapping.subject,
        property_iri=mapping.property_iri,
        historical_subject=historical,
        valid_at=valid_at,
        evaluated_at=evaluated_at,
        agreed_value=agreed,
        observations=tuple(view.receipt for view in views),
    )
