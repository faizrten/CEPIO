"""Fail-closed, provider-neutral host-bound Performance evidence acceptance."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.domain_bindings import ExternalRecordReference
from cepio.industry_iq import install_industry_iq_packs
from cepio.industry_performance_packs import drilling_contractor_performance_pack
from cepio.model import ObjectRef, OntologyObject
from cepio.performance_evidence_binding import (
    BoundEvidenceError,
    BoundEvidenceRequest,
    HostBoundPerformanceEvidenceService,
    HostEvidencePlan,
    HostEvidenceRecord,
)
from cepio.performance_industry_iq import (
    PERFORMANCE_RESPONSE_IQ_PACK,
    PerformanceIndustryIQService,
)
from cepio.performance_registry import InMemoryPerformanceContractStore, PerformanceContractRegistry
from cepio.performance_service import PerformanceService
from cepio.platform_bindings import (
    BindingCapability,
    BindingMode,
    BindingRuntimeStatus,
    EvidenceEnvelope,
    PlatformBindingManifest,
    register_evidence_binding,
)
from cepio.runtime import AuthorizationError
from scripts.drilling_performance_activation_v01 import (
    CONTRACT_ID,
    EVALUATED_AT,
    LEAKAGE,
    NPT,
    NPT_FORMULA,
    ORG,
    SAFETY,
    UPTIME,
    UPTIME_FORMULA,
    LEAKAGE_FORMULA,
    organization_overlay,
)

RIG = ObjectRef(id="rig-07", type="Equipment")
SOURCE = "fixture-authoritative-records"
CAP = "drilling.rig07.performance.read"


class FakeBoundEvidence:
    """Host-side fake transport. Readiness/identity do not attest real data."""

    manifest = PlatformBindingManifest(
        binding_id="synthetic-rig07-metric-source",
        provider_id="synthetic-fixture",
        source_system=SOURCE,
        mode=BindingMode.evidence,
        capabilities=frozenset(
            {BindingCapability.resolve_evidence, BindingCapability.versioned_identity}
        ),
    )

    def __init__(self, entries: dict[str, EvidenceEnvelope]):
        self.entries = entries
        self.calls: list[str] = []

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        self.calls.append(external_id)
        return self.entries[external_id]


def envelope(
    record_id: str,
    node_id: str,
    value: float,
    *,
    formula_ref: str | None = None,
    org: str = ORG,
    subject: str = RIG.id,
    source: str = SOURCE,
    kind: str = "performance-observation",
    version: str | None = "revision-001",
    observed_at=EVALUATED_AT,
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        reference=ExternalRecordReference(
            source_system=source,
            record_kind=kind,
            record_id=record_id,
            record_version=version,
        ),
        evidence={
            "organization_id": org,
            "subject_id": subject,
            "node_id": node_id,
            "value": value,
            "observed_at": observed_at.isoformat()
            if hasattr(observed_at, "isoformat")
            else observed_at,
            "formula_ref": formula_ref,
        },
    )


def entries() -> dict[str, EvidenceEnvelope]:
    return {
        "rig07-npt": envelope("rig07-npt", NPT, 0.10, formula_ref=NPT_FORMULA),
        "rig07-uptime": envelope("rig07-uptime", UPTIME, 0.90, formula_ref=UPTIME_FORMULA),
        "rig07-leakage": envelope("rig07-leakage", LEAKAGE, 32000.0, formula_ref=LEAKAGE_FORMULA),
        "rig07-safety": envelope("rig07-safety", SAFETY, 0.0),
    }


def plan() -> HostEvidencePlan:
    return HostEvidencePlan(
        plan_id="rig07-ceo-performance",
        organization_id=ORG,
        contract_id=CONTRACT_ID,
        contract_version="0.1.0",
        subject=RIG,
        focus_node_id=NPT,
        records=(
            HostEvidenceRecord(node_id=NPT, external_id="rig07-npt", max_age_seconds=3600),
            HostEvidenceRecord(node_id=UPTIME, external_id="rig07-uptime", max_age_seconds=3600),
            HostEvidenceRecord(
                node_id=LEAKAGE, external_id="rig07-leakage", max_age_seconds=3600, required=False
            ),
            HostEvidenceRecord(
                node_id=SAFETY, external_id="rig07-safety", max_age_seconds=3600, required=False
            ),
        ),
    )


def fixture(*, data=None, registered_status=BindingRuntimeStatus.ready, plan_override=None):
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id=RIG.id,
            type=RIG.type,
            name="SYNTHETIC Rig 07",
            properties={"sharingScope": "internal"},
        )
    )
    install_industry_iq_packs(runtime, [PERFORMANCE_RESPONSE_IQ_PACK])
    application = CEPIOApplicationService(runtime)
    registry = PerformanceContractRegistry(InMemoryPerformanceContractStore())
    registry.register(
        drilling_contractor_performance_pack(), activate=True, created_at=EVALUATED_AT
    )
    registry.register(organization_overlay(), activate=True, created_at=EVALUATED_AT)
    performance = PerformanceService(registry)
    binding = FakeBoundEvidence(data if data is not None else entries())
    registration = register_evidence_binding(binding, capability_id=CAP, status=registered_status)
    service = HostBoundPerformanceEvidenceService(
        performance, application, binding, registration, (plan_override or plan(),)
    )
    return service, binding, application, performance


def context(tenant=ORG, role="cepio_admin"):
    return ExecutionContext(
        actor_id="synthetic-rig07-ceo",
        actor_roles=frozenset({role}),
        tenant_id=tenant,
    )


def request():
    return BoundEvidenceRequest(plan_id="rig07-ceo-performance", evaluated_at=EVALUATED_AT)


def assert_error(code, callback):
    with pytest.raises(BoundEvidenceError) as exc:
        callback()
    assert exc.value.code == code


def test_host_resolution_produces_versioned_tenant_scoped_evidence_for_existing_iq():
    service, binding, application, performance = fixture()
    result = service.materialize(request(), context())

    assert binding.calls == ["rig07-npt", "rig07-uptime", "rig07-leakage", "rig07-safety"]
    assert result.organization_id == ORG
    assert result.evidence_status == "host_bound_source_not_attested"
    assert result.authority == "recommend_only"
    assert result.policy_required is True
    assert result.contract_version == "0.1.0"
    assert len(result.source_revision_hashes) == 2
    assert result.reasoning_request.contract_version == "0.1.0"
    assert result.reasoning_request.subject == RIG
    assert result.reasoning_request.observations == result.observations
    assert [entry.reference_key for entry in result.source_records] == [
        f"{SOURCE}:performance-observation:rig07-npt:revision-001",
        f"{SOURCE}:performance-observation:rig07-uptime:revision-001",
        f"{SOURCE}:performance-observation:rig07-leakage:revision-001",
        f"{SOURCE}:performance-observation:rig07-safety:revision-001",
    ]
    assert all(obs.source_subject_id == RIG.id for obs in result.observations)

    assessment = PerformanceIndustryIQService(performance, application).reason(
        result.reasoning_request, context()
    )
    assert assessment.deviation.status.value == "off_track"
    assert assessment.decision_proposal.recommended_action is None
    assert assessment.authority == "recommend_only"
    assert application.runtime.all_audits() == []


def test_no_caller_payload_fields_and_unconfigured_plan_fail_closed():
    service, binding, _, _ = fixture()
    assert_error(
        "PLAN_NOT_CONFIGURED",
        lambda: service.materialize(
            BoundEvidenceRequest(plan_id="not-registered", evaluated_at=EVALUATED_AT),
            context(),
        ),
    )
    assert binding.calls == []
    with pytest.raises(ValidationError):
        BoundEvidenceRequest.model_validate(
            {
                "plan_id": "rig07-ceo-performance",
                "evaluated_at": EVALUATED_AT,
                "observations": [{"value": 1}],
                "organization_id": "another-tenant",
            }
        )
    with pytest.raises(ValidationError):
        BoundEvidenceRequest(
            plan_id="rig07-ceo-performance", evaluated_at=EVALUATED_AT, simulation_only=False
        )


def test_tenant_rejected_before_source_access_and_no_runtime_write():
    service, binding, _, _ = fixture()
    assert_error(
        "ORGANIZATION_SCOPE_MISMATCH",
        lambda: service.materialize(request(), context("different-org")),
    )
    assert binding.calls == []


def test_source_registration_and_reference_version_required():
    service, binding, _, _ = fixture(registered_status=BindingRuntimeStatus.degraded)
    assert_error("BINDING_NOT_READY", lambda: service.materialize(request(), context()))
    assert binding.calls == []

    broken = entries()
    broken["rig07-npt"] = envelope("rig07-npt", NPT, 0.10, formula_ref=NPT_FORMULA, version=None)
    service, _, _, _ = fixture(data=broken)
    assert_error("SOURCE_PROVENANCE_MISMATCH", lambda: service.materialize(request(), context()))


def test_optional_evidence_is_missing_not_fabricated():
    data = entries()
    del data["rig07-leakage"]
    del data["rig07-safety"]
    service, _, _, performance = fixture(data=data)
    observed = service.materialize(request(), context())
    assert {item.node_id for item in observed.observations} == {NPT, UPTIME}
    evaluation = performance.evaluate(CONTRACT_ID, observed.observations, evaluated_at=EVALUATED_AT)
    assert evaluation.evaluation.node(LEAKAGE).status.value == "unknown"
    assert evaluation.evaluation.node(SAFETY).status.value == "unknown"


def test_required_evidence_is_missing_and_blocks_decision():
    data = entries()
    del data["rig07-npt"]
    service, _, _, _ = fixture(data=data)
    assert_error("REQUIRED_EVIDENCE_MISSING", lambda: service.materialize(request(), context()))


@pytest.mark.parametrize(
    ("bad", "code"),
    [
        ({"org": "another-org"}, "SOURCE_SCOPE_MISMATCH"),
        ({"subject": "rig-12"}, "SOURCE_SCOPE_MISMATCH"),
        ({"node": UPTIME}, "SOURCE_NODE_MISMATCH"),
        ({"formula": "logic://unapproved/v1"}, "FORMULA_MISMATCH"),
        ({"source": "forged-source"}, "SOURCE_PROVENANCE_MISMATCH"),
        ({"kind": "unapproved-document"}, "SOURCE_PROVENANCE_MISMATCH"),
        ({"version": ""}, "SOURCE_PROVENANCE_MISMATCH"),
        ({"time": EVALUATED_AT - timedelta(hours=3)}, "SOURCE_STALE"),
        ({"time": EVALUATED_AT + timedelta(minutes=1)}, "SOURCE_TIME_INVALID"),
        ({"time": EVALUATED_AT.replace(tzinfo=None)}, "SOURCE_TIME_INVALID"),
    ],
)
def test_source_payload_integrity_checks(bad, code):
    data = entries()
    data["rig07-npt"] = envelope(
        "rig07-npt",
        bad.get("node", NPT),
        0.10,
        formula_ref=bad.get("formula", NPT_FORMULA),
        org=bad.get("org", ORG),
        subject=bad.get("subject", RIG.id),
        source=bad.get("source", SOURCE),
        kind=bad.get("kind", "performance-observation"),
        version=bad.get("version", "revision-001"),
        observed_at=bad.get("time", EVALUATED_AT),
    )
    service, _, _, _ = fixture(data=data)
    assert_error(code, lambda: service.materialize(request(), context()))


def test_invalid_evidence_payload_does_not_become_observation():
    data = entries()
    bad = data["rig07-npt"]
    data["rig07-npt"] = EvidenceEnvelope(
        reference=bad.reference,
        evidence={**bad.evidence, "value": "not-a-number"},
    )
    service, _, _, _ = fixture(data=data)
    assert_error("INVALID_SOURCE_PAYLOAD", lambda: service.materialize(request(), context()))


def test_wrong_source_record_identity_is_rejected():
    data = entries()
    data["rig07-npt"] = envelope("different-record", NPT, 0.1, formula_ref=NPT_FORMULA)
    service, _, _, _ = fixture(data=data)
    assert_error("SOURCE_PROVENANCE_MISMATCH", lambda: service.materialize(request(), context()))


def test_invalid_configured_node_or_focus_is_rejected_before_reasoning():
    cfg = plan()
    cfg = cfg.model_copy(
        update={
            "records": cfg.records
            + (
                HostEvidenceRecord(
                    node_id="not-in-contract", external_id="x", max_age_seconds=3600
                ),
            )
        }
    )
    data = entries()
    data["x"] = envelope("x", "not-in-contract", 1.0)
    service, _, _, _ = fixture(data=data, plan_override=cfg)
    assert_error("NODE_NOT_FOUND", lambda: service.materialize(request(), context()))

    cfg = plan().model_copy(update={"focus_node_id": "not-in-contract"})
    service, binding, _, _ = fixture(plan_override=cfg)
    assert_error("FOCUS_NODE_MISSING", lambda: service.materialize(request(), context()))
    assert binding.calls == []


def test_host_plan_rejects_duplicate_and_optional_focus():
    cfg = plan()
    with pytest.raises(ValueError):
        HostEvidencePlan(**{**cfg.model_dump(), "records": (cfg.records[0], cfg.records[0])})
    with pytest.raises(ValueError):
        HostEvidencePlan(**{**cfg.model_dump(), "records": (cfg.records[1],)})
    with pytest.raises(ValueError):
        HostEvidencePlan(
            **{
                **cfg.model_dump(),
                "records": (
                    HostEvidenceRecord(
                        node_id=NPT, external_id="rig07-npt", max_age_seconds=3600, required=False
                    ),
                ),
            }
        )


def test_materializer_denies_object_reads_and_wrong_type():
    service, binding, _, _ = fixture()
    with pytest.raises(AuthorizationError):
        service.materialize(request(), context(role="unknown_role"))
    assert binding.calls == []
    cfg = plan().model_copy(update={"subject": ObjectRef(id=RIG.id, type="Well")})
    service, binding, _, _ = fixture(plan_override=cfg)
    assert_error("SUBJECT_TYPE_MISMATCH", lambda: service.materialize(request(), context()))
    assert binding.calls == []


def test_unregistered_version_capability_and_write_binding_rejected():
    service, binding, app, performance = fixture()
    no_version = FakeBoundEvidence(entries())
    no_version.manifest = no_version.manifest.model_copy(
        update={"capabilities": frozenset({BindingCapability.resolve_evidence})}
    )
    reg = register_evidence_binding(no_version, capability_id=CAP)
    assert_error(
        "VERSIONED_EVIDENCE_REQUIRED",
        lambda: HostBoundPerformanceEvidenceService(performance, app, no_version, reg, (plan(),)),
    )
    mismatch = register_evidence_binding(binding, capability_id=CAP).model_copy(
        update={"capability_id": "another-capability", "manifest": no_version.manifest}
    )
    assert_error(
        "BINDING_IDENTITY_MISMATCH",
        lambda: HostBoundPerformanceEvidenceService(performance, app, binding, mismatch, (plan(),)),
    )

    class UnsafeFake(FakeBoundEvidence):
        def write_governed(self):
            raise AssertionError("must not be called")

    unsafe = UnsafeFake(entries())
    reg = register_evidence_binding(binding, capability_id=CAP)
    assert_error(
        "READ_ONLY_BINDING_REQUIRED",
        lambda: HostBoundPerformanceEvidenceService(performance, app, unsafe, reg, (plan(),)),
    )


def test_naive_evaluation_time_and_duplicate_plan_fail_closed():
    service, binding, app, performance = fixture()
    assert_error(
        "TIMEZONE_REQUIRED",
        lambda: service.materialize(
            BoundEvidenceRequest(
                plan_id="rig07-ceo-performance", evaluated_at=EVALUATED_AT.replace(tzinfo=None)
            ),
            context(),
        ),
    )
    assert binding.calls == []
    with pytest.raises(ValueError):
        HostBoundPerformanceEvidenceService(
            performance,
            app,
            binding,
            register_evidence_binding(binding, capability_id=CAP),
            (plan(), plan()),
        )


def test_non_evidence_binding_mode_is_rejected():
    _, binding, application, performance = fixture()
    invalid_manifest = binding.manifest.model_copy(
        update={"mode": BindingMode.governed_action}
    )
    binding.manifest = invalid_manifest
    registration = register_evidence_binding(FakeBoundEvidence(entries()), capability_id=CAP)
    invalid_registration = registration.model_copy(update={"manifest": invalid_manifest})
    assert_error(
        "READ_ONLY_BINDING_REQUIRED",
        lambda: HostBoundPerformanceEvidenceService(
            performance, application, binding, invalid_registration, (plan(),)
        ),
    )
