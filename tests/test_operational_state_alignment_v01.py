"""Synthetic negative qualification of state alignment; no enterprise source access."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.domain_bindings import ExternalRecordReference
from cepio.model import ObjectRef, OntologyObject
from cepio.operational_state_alignment import (
    HostStateAlignmentPlan,
    StateAlignmentError,
    StateSourceSelection,
    assess_operational_state_alignment,
)
from cepio.operational_state_inspection import HostOperationalStatePlan, OperationalStateReadError
from cepio.platform_bindings import (
    BindingCapability,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
    register_evidence_binding,
)
from cepio.policy import RolePolicyEngine
from cepio.runtime import AuthorizationError


STATUS_IRI = "https://cepio.org/ontology/core#status"
VALID_STATES = ("running", "tripped", "degraded", "stopped")


class FakeStateSource:
    """Only a synthetic adapter; not an attested source or permission authority."""

    def __init__(self, name: str, observed_at: datetime, state: str = "tripped") -> None:
        self.manifest = PlatformBindingManifest(
            binding_id=f"synthetic-{name}",
            provider_id="synthetic",
            source_system=name,
            mode=BindingMode.evidence,
            capabilities=frozenset(
                {BindingCapability.resolve_evidence, BindingCapability.versioned_identity}
            ),
        )
        self.reference = ExternalRecordReference(
            source_system=name,
            record_kind="state-observation",
            record_id=f"{name}-R1",
            record_version="v1",
        )
        self.payload = {
            "organization_id": "tenant-A",
            "subject_id": "K-201",
            "observed_at": observed_at,
            "property_iri": STATUS_IRI,
            "state_value": state,
            "mapping_id": "k201-state-example",
            "mapping_version": "0.1",
        }
        self.calls = 0

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        self.calls += 1
        return EvidenceEnvelope(reference=self.reference, evidence=dict(self.payload))


def case(*, state: str = "tripped", sources_count: int = 2):
    now = datetime.now(timezone.utc)
    runtime = build_runtime(validate_types=False)
    runtime.policy_engine = RolePolicyEngine(
        {
            "viewer": {
                "read_types": ["Compressor"],
                "read_scopes": ["public"],
                "read_properties": {"Compressor": [STATUS_IRI]},
            },
            "no-access": {"read_types": []},
            "no-property": {
                "read_types": ["Compressor"],
                "read_scopes": ["public"],
                "read_properties": {"Compressor": ["criticality"]},
            },
        }
    )
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="Synthetic compressor",
            properties={
                STATUS_IRI: state,
                "criticality": "high",
                "sharingScope": "public",
            },
        )
    )
    svc = CEPIOApplicationService(runtime)
    mapping = HostStateAlignmentPlan(
        organization_id="tenant-A",
        subject=ObjectRef(id="K-201", type="Compressor"),
        property_iri=STATUS_IRI,
        mapping_id="k201-state-example",
        mapping_version="0.1",
        allowed_values=VALID_STATES,
    )
    srcs = []
    for i in range(sources_count):
        name = f"synthetic-{i + 1}"
        adapter = FakeStateSource(name, now)
        registration = register_evidence_binding(adapter, capability_id="state-observation")
        plan = HostOperationalStatePlan(
            plan_id=f"plan-{i + 1}",
            organization_id="tenant-A",
            capability_id="state-observation",
            subject=mapping.subject,
            external_id=adapter.reference.record_id,
            record_kind="state-observation",
            max_age_seconds=120,
        )
        srcs.append(
            StateSourceSelection(
                binding=adapter,
                registration=registration,
                plan=plan,
                role="primary" if i == 0 else "corroborating",
            )
        )
    ctx = ExecutionContext(
        actor_id="trusted-local-host",
        actor_roles=frozenset({"viewer"}),
        tenant_id="tenant-A",
    )
    return svc, mapping, tuple(srcs), ctx, now + timedelta(seconds=15), now + timedelta(seconds=25)


def run(config):
    svc, mapping, sources, context, valid_at, evaluated_at = config
    return assess_operational_state_alignment(
        svc,
        mapping,
        sources,
        context,
        valid_at=valid_at,
        evaluated_at=evaluated_at,
    )


def block(config, code: str) -> None:
    with pytest.raises(StateAlignmentError) as exc:
        run(config)
    assert exc.value.code == code


def test_two_independent_consistent_source_claims_are_only_non_authoritative_candidate():
    config = case()
    output = run(config)
    assert output.status == "consistent_candidate"
    assert output.agreed_value == "tripped"
    assert output.subject.id == "K-201"
    assert output.property_iri == STATUS_IRI
    assert output.historical_subject.properties == {STATUS_IRI: "tripped"}
    assert len(output.observations) == 2
    assert {r.source_system for r in output.observations} == {"synthetic-1", "synthetic-2"}
    assert all(r.authenticity == "not_attested" for r in output.observations)
    assert output.source_authenticity == "not_attested"
    assert output.state_authority == "not_qualified"
    assert output.decision_eligible is False
    assert all(spec.binding.calls == 1 for spec in config[2])
    assert config[0].runtime.list_decisions() == []
    assert config[0].runtime.all_audits() == []
    assert config[0].runtime.get_object("K-201").version == 1


def test_conflicting_source_observations_block_the_state_claim_without_priority_override():
    config = case()
    config[2][1].binding.payload["state_value"] = "running"
    result = run(config)
    assert result.status == "conflict_blocked"
    assert result.agreed_value is None
    assert result.decision_eligible is False


def test_agreeing_sources_do_not_override_historical_object_mismatch():
    result = run(case(state="degraded"))
    assert result.status == "historical_mismatch"
    assert result.agreed_value is None


def test_single_source_is_not_independent_corroboration():
    result = run(case(sources_count=1))
    assert result.status == "insufficient_independent_sources"
    assert result.agreed_value is None


def test_two_bindings_from_same_upstream_system_are_not_independent():
    config = case()
    second = config[2][1].binding
    second.manifest = second.manifest.model_copy(update={"source_system": "synthetic-1"})
    second.reference = second.reference.model_copy(update={"source_system": "synthetic-1"})
    original = config[2][1]
    config[2] = (
        config[2][0],
        StateSourceSelection(
            binding=second,
            registration=register_evidence_binding(second, capability_id="state-observation"),
            plan=original.plan,
            role=original.role,
        ),
    )
    result = run(config)
    assert result.status == "insufficient_independent_sources"


def test_wrong_tenant_rejected_before_source_read():
    config = list(case())
    config[3] = config[3].model_copy(update={"tenant_id": "tenant-B"})
    block(tuple(config), "TENANT_DENIED")
    assert all(spec.binding.calls == 0 for spec in config[2])


def test_unauthorized_object_rejected_before_source_read():
    config = list(case())
    config[3] = config[3].model_copy(update={"actor_roles": frozenset({"no-access"})})
    with pytest.raises(AuthorizationError):
        run(tuple(config))
    assert all(spec.binding.calls == 0 for spec in config[2])


def test_no_property_visibility_rejected_before_source_read():
    config = list(case())
    config[3] = config[3].model_copy(update={"actor_roles": frozenset({"no-property"})})
    block(tuple(config), "STATE_PROPERTY_NOT_VISIBLE")
    assert all(spec.binding.calls == 0 for spec in config[2])


@pytest.mark.parametrize(
    ("source_count", "expected"),
    [(0, "SOURCE_COUNT_INVALID"), (5, "SOURCE_COUNT_INVALID")],
)
def test_bounded_source_count(source_count, expected):
    config = list(case(sources_count=source_count))
    block(tuple(config), expected)


def test_primary_role_and_duplicate_reference_controls():
    config = list(case())
    config[2] = tuple(
        StateSourceSelection(
            binding=item.binding,
            registration=item.registration,
            plan=item.plan,
            role="corroborating",
        )
        for item in config[2]
    )
    block(tuple(config), "PRIMARY_REQUIRED")

    config = list(case())
    config[2] = (config[2][0], config[2][0])
    block(tuple(config), "PRIMARY_REQUIRED")

    config = list(case())
    second = config[2][1]
    config[2] = (
        config[2][0],
        StateSourceSelection(
            binding=config[2][0].binding,
            registration=config[2][0].registration,
            plan=config[2][0].plan,
            role=second.role,
        ),
    )
    block(tuple(config), "DUPLICATE_SOURCE")


def test_unknown_source_role_rejected():
    config = list(case())
    config[2] = (
        config[2][0],
        StateSourceSelection(
            binding=config[2][1].binding,
            registration=config[2][1].registration,
            plan=config[2][1].plan,
            role="untrusted",  # type: ignore[arg-type]
        ),
    )
    block(tuple(config), "SOURCE_ROLE_INVALID")


def test_blank_allowed_state_rejected():
    config = list(case())
    config[1] = config[1].model_copy(update={"allowed_values": (" ", "running")})
    block(tuple(config), "ALLOWED_VALUES_INVALID")


def test_source_scope_plan_mismatch_denied_before_read():
    config = list(case())
    wrong = config[2][0].plan.model_copy(update={"organization_id": "tenant-other"})
    source = config[2][0]
    config[2] = (
        StateSourceSelection(
            binding=source.binding,
            registration=source.registration,
            plan=wrong,
            role=source.role,
        ),
        config[2][1],
    )
    block(tuple(config), "PLAN_SCOPE_MISMATCH")
    assert all(spec.binding.calls == 0 for spec in config[2])


def test_canonical_registry_and_type_guards():
    config = list(case())
    config[0].runtime.property_registry = None
    block(tuple(config), "PROPERTY_REGISTRY_REQUIRED")

    config = list(case())
    config[1] = config[1].model_copy(update={"property_iri": "https://invalid/unknown"})
    block(tuple(config), "PROPERTY_UNDECLARED")

    config = list(case())
    config[1] = config[1].model_copy(update={"property_iri": "cepio:status"})
    block(tuple(config), "PROPERTY_UNSUPPORTED")

    config = list(case())
    config[1] = config[1].model_copy(
        update={"property_iri": "https://cepio.org/ontology/core#value"}
    )
    block(tuple(config), "PROPERTY_UNSUPPORTED")

    config = list(case())
    config[1] = config[1].model_copy(update={"subject": ObjectRef(id="K-201", type="Pump")})
    altered = tuple(
        StateSourceSelection(
            binding=s.binding,
            registration=s.registration,
            plan=s.plan.model_copy(update={"subject": config[1].subject}),
            role=s.role,
        )
        for s in config[2]
    )
    config[2] = altered
    block(tuple(config), "SUBJECT_TYPE_MISMATCH")


@pytest.mark.parametrize(
    ("corrupt", "code"),
    [
        ("property_iri", "MAPPING_MISMATCH"),
        ("mapping_id", "MAPPING_MISMATCH"),
        ("mapping_version", "MAPPING_MISMATCH"),
        ("state_value", "STATE_VALUE_UNSUPPORTED"),
    ],
)
def test_tampered_mapping_contract_fails_closed(corrupt, code):
    config = case()
    config[2][0].binding.payload[corrupt] = "unrecognized"
    block(config, code)


@pytest.mark.parametrize("key", ["organization_id", "subject_id"])
def test_source_scope_tampering_rejected_by_m2(key):
    config = case()
    config[2][0].binding.payload[key] = "tenant-or-subject-other"
    with pytest.raises(OperationalStateReadError) as exc:
        run(config)
    assert exc.value.code == "SOURCE_SCOPE_MISMATCH"


def test_source_payload_extra_field_and_missing_value_fail_strictly():
    config = case()
    config[2][0].binding.payload["unknown_column"] = "secret"
    block(config, "SOURCE_STATE_INVALID")

    config = case()
    del config[2][0].binding.payload["state_value"]
    block(config, "SOURCE_STATE_INVALID")


def test_no_host_source_write_surface_allowed():
    config = case()
    config[2][0].binding.write_governed = lambda *args: None
    block(config, "READ_ONLY_REQUIRED")
    assert config[2][0].binding.calls == 0


def test_stale_source_does_not_become_candidate():
    config = case()
    config[2][1].binding.payload["observed_at"] = config[4] - timedelta(seconds=121)
    with pytest.raises(OperationalStateReadError) as exc:
        run(config)
    assert exc.value.code == "SOURCE_STALE"


def test_historical_property_visibility_rechecked_after_current_read(monkeypatch):
    config = case()
    historical = config[0].runtime.get_object("K-201").model_copy(deep=True)
    historical.properties.pop(STATUS_IRI)
    monkeypatch.setattr(
        config[0].runtime,
        "get_object_valid_at",
        lambda *args, **kwargs: historical,
    )
    block(config, "HISTORICAL_PROPERTY_DENIED")


def test_rejects_historical_non_string_state(monkeypatch):
    config = case()
    historical = config[0].runtime.get_object("K-201").model_copy(deep=True)
    historical.properties[STATUS_IRI] = 7
    monkeypatch.setattr(
        config[0].runtime,
        "get_object_valid_at",
        lambda *args, **kwargs: historical,
    )
    block(config, "HISTORICAL_VALUE_UNSUPPORTED")


def test_rejects_inspection_snapshot_drift_between_sources(monkeypatch):
    config = case()
    base = config[0].runtime.get_object("K-201").model_copy(deep=True)
    counter = {"reads": 0}

    def changed_snapshot(*args, **kwargs):
        counter["reads"] += 1
        snap = base.model_copy(deep=True)
        if counter["reads"] == 2:
            snap.name = "A different historical object snapshot"
        return snap

    monkeypatch.setattr(config[0].runtime, "get_object_valid_at", changed_snapshot)
    block(config, "SNAPSHOT_MISMATCH")
