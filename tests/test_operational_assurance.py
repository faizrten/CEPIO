from pathlib import Path

from cepio.operational_assurance import (
    EvidenceBundle,
    EvidenceRecord,
    OperatorAnswer,
    run_operational_assurance,
    validate_operator_answer,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "generalization/runtime/drilling-contractor-operational-assurance-v0.4.yaml"


def _report():
    return run_operational_assurance(ROOT, SCENARIO)


def test_operational_assurance_passes_all_deterministic_gates():
    report = _report()
    assert report["assurance_version"] == "0.4"
    assert report["mode"] == "deterministic-operational-assurance"
    assert report["gate_count"] == 5
    assert report["status_counts"] == {"PASS": 5, "FAIL": 0, "ERROR": 0}
    assert report["assurance_pass_rate"] == 1.0
    assert report["dimension_status"] == {
        "temporal": "PASS",
        "provenance": "PASS",
        "authority": "PASS",
        "policy+kinetic": "PASS",
        "operator-evidence": "PASS",
    }


def test_operational_assurance_references_frozen_v03_questions():
    report = _report()
    assert report["competency_pack"].endswith("drilling-contractor-persona-capabilities-v0.3.yaml")
    assert set(report["referenced_questions"]) == {
        "DC-PC-001",
        "DC-PC-002",
        "DC-PC-004",
        "DC-PC-005",
    }


def test_agent_is_recommend_only_and_human_action_retains_decision_audit_link():
    report = _report()
    governed = next(result for result in report["results"] if result["dimension"] == "policy+kinetic")
    assert governed["details"]["agent_action_status"] == "rejected"
    assert governed["details"]["agent_policy_effect"] == "recommend_only"
    assert governed["details"]["human_action_status"] == "executed"
    assert governed["details"]["human_policy_effect"] == "allow"
    assert governed["details"]["decision_id"]
    assert governed["details"]["audit_id"]


def test_authority_is_resolved_through_assignment_not_direct_person_rig_edge():
    report = _report()
    authority = next(result for result in report["results"] if result["dimension"] == "authority")
    assert authority["details"]["authority_holder_id"] == "PERSON-RT-OIM-001"
    assert authority["details"]["resolved_holder_ids"] == ["PERSON-RT-OIM-001"]


def test_operator_answer_rejects_unknown_evidence_ids():
    bundle = EvidenceBundle(
        question_id="CQ-TEST",
        scenario_id="scenario-test",
        answer_facts={"status": "known"},
        records=[EvidenceRecord(id="evidence:1", kind="audit", payload={"ok": True})],
        bundle_hash="test-hash",
    )
    accepted = validate_operator_answer(
        OperatorAnswer(status="ANSWERED", answer="Supported", evidence_ids=["evidence:1"]),
        bundle,
    )
    rejected = validate_operator_answer(
        OperatorAnswer(status="ANSWERED", answer="Hallucinated", evidence_ids=["evidence:missing"]),
        bundle,
    )
    assert accepted.status == "ANSWERED"
    assert rejected.status == "REJECTED_UNSUPPORTED_EVIDENCE"
    assert rejected.answer is None
