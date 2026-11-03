from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.domain_bindings import ExternalRecordReference
from cepio.model import ObjectRef, OntologyObject
from cepio.operational_state_inspection import (
    HostOperationalStatePlan,
    OperationalStateReadError,
    inspect_operational_state,
)
from cepio.platform_bindings import (
    BindingCapability,
    BindingMode,
    BindingRuntimeStatus,
    EvidenceEnvelope,
    PlatformBindingManifest,
    register_evidence_binding,
)
from cepio.policy import RolePolicyEngine
from cepio.runtime import AuthorizationError


class FakeObservationBinding:
    def __init__(self, observed_at: datetime) -> None:
        self.manifest = PlatformBindingManifest(
            binding_id="synthetic-versioned-observation",
            provider_id="synthetic",
            source_system="synthetic-observation-source",
            mode=BindingMode.evidence,
            capabilities=frozenset(
                {BindingCapability.resolve_evidence, BindingCapability.versioned_identity}
            ),
        )
        self.reference = ExternalRecordReference(
            source_system=self.manifest.source_system,
            record_kind="normalized-observation",
            record_id="OBS-201",
            record_version="7",
        )
        self.payload = {
            "organization_id": "tenant-A",
            "subject_id": "K-201",
            "observed_at": observed_at,
        }
        self.calls = 0
        self.missing = False

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        self.calls += 1
        if self.missing:
            raise KeyError("not found")
        return EvidenceEnvelope(reference=self.reference, evidence=self.payload)


def configured_case():
    now = datetime.now(timezone.utc)
    runtime = build_runtime(validate_types=False, validate_properties=False)
    runtime.policy_engine = RolePolicyEngine(
        {
            "viewer": {
                "read_types": ["Compressor"],
                "read_scopes": ["public"],
                "read_properties": {"Compressor": ["criticality"]},
            },
            "outsider": {"read_types": []},
        }
    )
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="Synthetic K-201",
            properties={
                "criticality": "high",
                "operatingState": "degraded",
                "sharingScope": "public",
            },
        )
    )
    service = CEPIOApplicationService(runtime)
    binding = FakeObservationBinding(now)
    registration = register_evidence_binding(binding, capability_id="condition-observation")
    plan = HostOperationalStatePlan(
        plan_id="k201-inspection",
        organization_id="tenant-A",
        capability_id="condition-observation",
        subject=ObjectRef(id="K-201", type="Compressor"),
        external_id="OBS-201",
        record_kind="normalized-observation",
        max_age_seconds=180,
    )
    context = ExecutionContext(
        actor_id="host-viewer",
        actor_roles=frozenset({"viewer"}),
        tenant_id="tenant-A",
    )
    valid_at = now + timedelta(seconds=20)
    evaluated_at = valid_at + timedelta(seconds=10)
    return service, binding, registration, plan, context, valid_at, evaluated_at


def inspect_case(case):
    service, binding, registration, plan, context, valid_at, evaluated_at = case
    return inspect_operational_state(
        service,
        binding,
        registration,
        plan,
        context,
        valid_at=valid_at,
        evaluated_at=evaluated_at,
    )


def assert_blocked(case, code: str) -> None:
    with pytest.raises(OperationalStateReadError) as exc:
        inspect_case(case)
    assert exc.value.code == code


def test_read_only_temporal_state_and_versioned_observation_receipt():
    case = configured_case()
    service, binding, _, _, _, valid_at, _ = case
    result = inspect_case(case)
    assert result.object_inspection.context.subject.id == "K-201"
    assert result.historical_subject.properties == {"criticality": "high"}
    assert result.valid_at == valid_at
    assert result.receipt.record_id == "OBS-201"
    assert result.receipt.record_version == "7"
    assert result.receipt.freshness == "within_configured_window"
    assert result.receipt.authenticity == "not_attested"
    assert result.source_to_state_alignment == "not_proven"
    assert result.action_authority == "not_evaluated"
    assert result.receipt.age_seconds == pytest.approx(20)
    assert "operatingState" not in result.model_dump_json()
    assert binding.calls == 1
    assert service.runtime.list_decisions() == []
    assert service.runtime.all_audits() == []


def test_tenant_denial_precedes_object_and_source_access():
    case = list(configured_case())
    case[4] = case[4].model_copy(update={"tenant_id": "other"})
    assert_blocked(tuple(case), "TENANT_DENIED")
    assert case[1].calls == 0


def test_actor_denial_precedes_source_lookup():
    case = list(configured_case())
    case[4] = case[4].model_copy(update={"actor_roles": frozenset({"outsider"})})
    with pytest.raises(AuthorizationError):
        inspect_case(tuple(case))
    assert case[1].calls == 0


def test_historical_scope_denial_is_separate_from_current_read():
    case = list(configured_case())
    service = case[0]
    before = datetime.now(timezone.utc) - timedelta(minutes=30)
    service.runtime.upsert_object(
        OntologyObject(
            id="OLDER",
            type="Compressor",
            name="Older restricted",
            properties={
                "criticality": "high",
                "sharingScope": "restricted",
                "validFrom": (before - timedelta(minutes=5)).isoformat(),
                "validTo": (before + timedelta(minutes=5)).isoformat(),
            },
        )
    )
    service.runtime.upsert_object(
        OntologyObject(
            id="OLDER",
            type="Compressor",
            name="Now visible",
            properties={
                "criticality": "high",
                "sharingScope": "public",
                "validFrom": (before + timedelta(minutes=5)).isoformat(),
            },
        ),
        expected_version=1,
    )
    case[3] = case[3].model_copy(update={"subject": ObjectRef(id="OLDER", type="Compressor")})
    case[5] = before
    assert_blocked(tuple(case), "HISTORY_DENIED")
    assert case[1].calls == 0


@pytest.mark.parametrize(
    ("corruption", "expected"),
    [
        ("source_system", "SOURCE_IDENTITY_MISMATCH"),
        ("record_id", "SOURCE_IDENTITY_MISMATCH"),
        ("record_kind", "SOURCE_IDENTITY_MISMATCH"),
        ("record_version", "SOURCE_IDENTITY_MISMATCH"),
        ("organization_id", "SOURCE_SCOPE_MISMATCH"),
        ("subject_id", "SOURCE_SCOPE_MISMATCH"),
        ("missing_time", "SOURCE_METADATA_INVALID"),
        ("future_time", "SOURCE_TIME_INVALID"),
        ("naive_time", "SOURCE_TIME_INVALID"),
        ("stale", "SOURCE_STALE"),
    ],
)
def test_corrupt_or_stale_source_evidence_fails_closed(corruption, expected):
    case = list(configured_case())
    binding = case[1]
    if corruption == "source_system":
        binding.reference = binding.reference.model_copy(update={"source_system": "wrong"})
    elif corruption == "record_id":
        binding.reference = binding.reference.model_copy(update={"record_id": "OTHER"})
    elif corruption == "record_kind":
        binding.reference = binding.reference.model_copy(update={"record_kind": "OTHER"})
    elif corruption == "record_version":
        binding.reference = binding.reference.model_copy(update={"record_version": None})
    elif corruption == "organization_id":
        binding.payload["organization_id"] = "wrong"
    elif corruption == "subject_id":
        binding.payload["subject_id"] = "OTHER"
    elif corruption == "missing_time":
        del binding.payload["observed_at"]
    elif corruption == "future_time":
        binding.payload["observed_at"] = case[5] + timedelta(seconds=1)
    elif corruption == "naive_time":
        binding.payload["observed_at"] = datetime.now()
    else:
        binding.payload["observed_at"] = case[5] - timedelta(seconds=181)
    assert_blocked(tuple(case), expected)
    assert binding.calls == 1


def test_missing_record_returns_non_disclosing_error():
    case = list(configured_case())
    case[1].missing = True
    assert_blocked(tuple(case), "SOURCE_MISSING")


def test_binding_config_and_version_contracts_fail_without_source_read():
    case = list(configured_case())
    case[2] = case[2].model_copy(update={"status": BindingRuntimeStatus.degraded})
    assert_blocked(tuple(case), "BINDING_NOT_READY")
    assert case[1].calls == 0

    case = list(configured_case())
    case[3] = case[3].model_copy(update={"capability_id": "wrong"})
    assert_blocked(tuple(case), "BINDING_MISMATCH")
    assert case[1].calls == 0

    case = list(configured_case())
    case[1].manifest = case[1].manifest.model_copy(
        update={"capabilities": frozenset({BindingCapability.resolve_evidence})}
    )
    case[2] = case[2].model_copy(update={"manifest": case[1].manifest})
    assert_blocked(tuple(case), "READ_ONLY_VERSIONED_REQUIRED")
    assert case[1].calls == 0


def test_time_window_errors_are_fail_closed():
    case = list(configured_case())
    case[5] = case[6] + timedelta(seconds=1)
    assert_blocked(tuple(case), "TIME_INVALID")
    case = list(configured_case())
    case[5] = datetime.now()
    assert_blocked(tuple(case), "TIMEZONE_REQUIRED")


def test_no_history_and_mismatched_subject_are_rejected_before_source():
    case = list(configured_case())
    case[5] = datetime(2000, 1, 1, tzinfo=timezone.utc)
    assert_blocked(tuple(case), "HISTORY_MISSING")
    assert case[1].calls == 0

    case = list(configured_case())
    case[3] = case[3].model_copy(update={"subject": ObjectRef(id="K-201", type="Pump")})
    assert_blocked(tuple(case), "SUBJECT_TYPE_MISMATCH")
    assert case[1].calls == 0
