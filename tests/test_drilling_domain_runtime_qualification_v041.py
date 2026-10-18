from datetime import datetime, timezone
from pathlib import Path

import pytest

from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.operational_assurance import EvidenceBundle, EvidenceRecord
from cepio.qualification_assurance import (
    evaluate_outcome_assessment,
    evaluate_plan_revision_authority,
    evaluate_prediction_freshness,
    evaluate_recommendation_evidence,
)
from cepio.runtime_coverage import run_runtime_coverage

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "generalization/runtime/drilling-contractor-domain-qualification-runtime-v0.4.1.yaml"


def _runtime():
    return build_runtime(resource_root=ROOT, validate_types=False, validate_properties=False)


def _put(runtime, object_id: str, object_type: str, name: str, properties=None):
    return runtime.upsert_object(
        OntologyObject(
            id=object_id,
            type=object_type,
            name=name,
            properties=properties or {},
        )
    )


def _rel(runtime, rel_type: str, source: OntologyObject, target: OntologyObject):
    return runtime.add_relationship(
        Relationship(
            type=rel_type,
            source=ObjectRef(id=source.id, type=source.type),
            target=ObjectRef(id=target.id, type=target.type),
        )
    )


def test_domain_qualification_runtime_is_15_of_15_with_evidence_gate():
    report = run_runtime_coverage(ROOT, SUITE)

    assert report["runtime_coverage_version"] == "0.4.1"
    assert report["question_count"] == 15
    assert report["status_counts"] == {"PASS": 15, "FAIL": 0, "ERROR": 0}
    assert report["runtime_coverage_rate"] == pytest.approx(1.0)
    assert all(result["operator_evidence_gate"]["passed"] for result in report["results"])
    assert [result["question_id"] for result in report["results"]] == [
        f"DC-DQ-{index:03d}" for index in range(1, 16)
    ]


def test_stale_prediction_is_rejected_as_current_enterprise_context():
    at = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    current = OntologyObject(
        id="PRED-CURRENT",
        type="https://cepio.org/ontology/agentic#Prediction",
        name="Current prediction",
        properties={
            "https://cepio.org/ontology/core#validFrom": "2026-10-17T10:00:00+00:00",
            "https://cepio.org/ontology/core#validTo": "2026-10-17T14:00:00+00:00",
        },
    )
    stale = current.model_copy(
        update={
            "id": "PRED-STALE",
            "name": "Stale prediction",
            "properties": {
                "https://cepio.org/ontology/core#validFrom": "2026-10-17T06:00:00+00:00",
                "https://cepio.org/ontology/core#validTo": "2026-10-17T08:00:00+00:00",
            },
        }
    )

    assert evaluate_prediction_freshness(current, at=at).status == "PASS"
    rejected = evaluate_prediction_freshness(stale, at=at)
    assert rejected.status == "REJECTED"
    assert rejected.reason == "prediction-is-stale-or-has-no-validity-window"


def test_recommendation_without_enterprise_evidence_is_withheld():
    runtime = _runtime()
    unsupported = _put(
        runtime,
        "REC-UNSUPPORTED",
        "https://cepio.org/ontology/agentic#Recommendation",
        "Unsupported recommendation",
    )
    supported = _put(
        runtime,
        "REC-SUPPORTED",
        "https://cepio.org/ontology/agentic#Recommendation",
        "Supported recommendation",
    )
    evidence = _put(
        runtime,
        "BOP-TEST-EVIDENCE",
        "https://cepio.org/ontology/drilling#WellControlTest",
        "BOP pressure test",
    )
    _rel(
        runtime,
        "https://cepio.org/ontology/agentic#supportedByEvidence",
        supported,
        evidence,
    )

    rejected = evaluate_recommendation_evidence(runtime, unsupported.id)
    accepted = evaluate_recommendation_evidence(runtime, supported.id)
    assert rejected.status == "REJECTED"
    assert rejected.reason == "recommendation-has-no-supporting-enterprise-evidence"
    assert accepted.status == "PASS"
    assert accepted.evidence_ids == [evidence.id]


def test_plan_revision_requires_current_scoped_authority():
    runtime = _runtime()
    at = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    plan = _put(
        runtime, "PLAN-1", "https://cepio.org/ontology/kinetic#OperationalPlan", "Original plan"
    )
    revision = _put(
        runtime, "REV-1", "https://cepio.org/ontology/kinetic#PlanRevision", "Plan revision"
    )
    decision = _put(
        runtime, "DEC-1", "https://cepio.org/ontology/kinetic#Decision", "Authorization decision"
    )
    rig = _put(runtime, "RIG-1", "https://cepio.org/ontology/drilling#OperatingRig", "Scoped rig")
    holder = _put(
        runtime, "AUTH-HOLDER-1", "https://cepio.org/ontology/workforce#CrewMember", "Company Man"
    )
    authority = _put(
        runtime,
        "AUTH-1",
        "https://cepio.org/ontology/workforce#AuthorityAssignment",
        "Plan-change authority",
        properties={
            "https://cepio.org/ontology/core#validFrom": "2026-10-17T08:00:00+00:00",
            "https://cepio.org/ontology/core#validTo": "2026-10-17T18:00:00+00:00",
        },
    )

    _rel(runtime, "https://cepio.org/ontology/kinetic#revisesPlan", revision, plan)
    _rel(runtime, "https://cepio.org/ontology/kinetic#authorizesRevision", decision, revision)
    _rel(runtime, "https://cepio.org/ontology/core#impacts", revision, rig)
    _rel(runtime, "https://cepio.org/ontology/workforce#authorityForAsset", authority, rig)
    _rel(runtime, "https://cepio.org/ontology/workforce#authorityHolder", authority, holder)

    accepted = evaluate_plan_revision_authority(runtime, revision.id, actor_id=holder.id, at=at)
    wrong_actor = evaluate_plan_revision_authority(
        runtime, revision.id, actor_id="UNAUTHORIZED-ACTOR", at=at
    )
    expired = evaluate_plan_revision_authority(
        runtime,
        revision.id,
        actor_id=holder.id,
        at=datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc),
    )

    assert accepted.status == "PASS"
    assert wrong_actor.status == "REJECTED"
    assert expired.status == "REJECTED"
    assert wrong_actor.reason == "actor-lacks-current-authority-for-plan-revision-scope"


def test_value_realization_requires_kpi_risk_and_provenance_chain():
    runtime = _runtime()
    assessment = _put(
        runtime,
        "ASSESS-1",
        "https://cepio.org/ontology/performance#OutcomeAssessment",
        "Outcome assessment",
    )
    decision = _put(
        runtime, "DEC-VAL-1", "https://cepio.org/ontology/kinetic#Decision", "Intervention decision"
    )
    kpi = _put(
        runtime, "KPI-VAL-1", "https://cepio.org/ontology/performance#KPIObservation", "NPT outcome"
    )
    risk = _put(runtime, "RISK-VAL-1", "https://cepio.org/ontology/core#Risk", "Safety risk")
    _rel(
        runtime, "https://cepio.org/ontology/performance#assessmentOfDecision", assessment, decision
    )
    _rel(runtime, "https://cepio.org/ontology/performance#observedOutcome", assessment, kpi)
    _rel(runtime, "https://cepio.org/ontology/performance#considersRisk", assessment, risk)

    insufficient = EvidenceBundle(
        question_id="DC-DQ-015",
        scenario_id="negative",
        answer_facts={},
        records=[
            EvidenceRecord(id="snapshot", kind="object_snapshot", payload={"object_id": kpi.id})
        ],
        bundle_hash="negative",
    )
    rejected = evaluate_outcome_assessment(runtime, assessment.id, evidence=insufficient)
    assert rejected.status == "REJECTED"
    assert rejected.reason == "outcome-assessment-lacks-provenance-chain"

    sufficient = EvidenceBundle(
        question_id="DC-DQ-015",
        scenario_id="positive",
        answer_facts={},
        records=[
            EvidenceRecord(
                id="source",
                kind="source_reference",
                payload={"source_record_id": "DDR-123", "outcome_id": kpi.id, "risk_id": risk.id},
            ),
            EvidenceRecord(
                id="provenance",
                kind="property_provenance",
                payload={"object_id": kpi.id, "risk_context": risk.id},
            ),
            EvidenceRecord(
                id="transform",
                kind="transformation",
                payload={
                    "mapping_id": "npt-kpi-v1",
                    "output_object_id": kpi.id,
                    "risk_context": risk.id,
                },
            ),
        ],
        bundle_hash="positive",
    )
    accepted = evaluate_outcome_assessment(runtime, assessment.id, evidence=sufficient)
    assert accepted.status == "PASS"
    assert accepted.details["outcome_ids"] == [kpi.id]
    assert accepted.details["risk_ids"] == [risk.id]
