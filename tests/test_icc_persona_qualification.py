from copy import deepcopy
from pathlib import Path

import cepio.icc_qualification as icc
from cepio.domain_onboarding import run_domain_onboarding
from cepio.generalization import load_pack


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/drilling-contractor-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def _rig_manager_question_id() -> str:
    pack = load_pack(
        ROOT / "generalization/competency/drilling-contractor-persona-capabilities-v0.3.yaml"
    )
    return next(question.id for question in pack.questions if "rig-manager" in question.personas)


def test_rig_manager_icc_is_persona_scoped_and_reuses_existing_capabilities():
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["qualification_status"] == "QUALIFIED"
    assert report["domain"] == "drilling-contractor"
    assert report["persona_id"] == "rig-manager"
    assert report["persona_binding"]["role"] == "Rig Manager"
    assert report["persona_binding"]["selection_source"] == "explicit-persona-binding"
    assert report["persona_binding"]["binding_id"] == "drilling-contractor-rig-manager-binding-v0.1"
    assert report["persona_binding"]["question_count"] == 14
    assert report["qualification"]["semantic_pass_rate"] == 1.0
    assert report["qualification"]["runtime_coverage_rate"] == 1.0
    assert report["icc_delta"]["required_question_ids"] == [
        f"DC-PC-{index:03d}" for index in range(1, 15)
    ]
    assert report["icc_delta"]["required_capabilities"]
    assert len(report["icc_delta"]["reused_capabilities"]) == len(
        report["icc_delta"]["required_capabilities"]
    )
    assert report["icc_delta"]["missing_capabilities"] == []
    assert report["icc_delta"]["new_semantic_candidates"] == []
    assert report["icc_delta"]["runtime_gaps"] == []
    assert report["icc_delta"]["policy_authority_gaps"] == []
    assert report["human_review_required"] is True
    assert len(report["provenance"]["manifest_sha256"]) == 64
    assert len(report["provenance"]["persona_binding_sha256"]) == 64
    assert len(report["provenance"]["persona_scope_hash"]) == 64


def test_icc_persona_qualification_fails_closed_for_unknown_persona():
    report = icc.run_icc_persona_qualification(
        ROOT,
        MANIFEST,
        WORKFLOW,
        POLICY,
        persona_id="not-a-real-persona",
    )

    assert report["status"] == "BLOCKED"
    assert report["current_state"] == "BLOCKED"
    assert "not declared in the scoped persona pack" in report["block_reason"]


def test_icc_persona_qualification_fails_closed_on_semantic_gap(monkeypatch):
    domain_report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    question_id = _rig_manager_question_id()
    mutated = deepcopy(domain_report)
    result = next(
        item for item in mutated["semantic_baseline"]["results"] if item["id"] == question_id
    )
    result["status"] = "PARTIAL"
    result["checks_passed"] = max(0, int(result["checks_total"]) - 1)
    result["missing"] = ["urn:test:persona-semantic-gap"]

    monkeypatch.setattr(icc, "run_domain_onboarding", lambda *args, **kwargs: mutated)
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["icc_delta"]["new_semantic_candidates"]
    assert "persona semantic pass rate" in report["block_reason"]


def test_icc_persona_qualification_fails_closed_on_runtime_gap(monkeypatch):
    domain_report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    question_id = _rig_manager_question_id()
    mutated = deepcopy(domain_report)
    runtime_result = next(
        item
        for item in mutated["runtime_qualification"]["results"]
        if item["question_id"] == question_id
    )
    runtime_result["status"] = "FAIL"

    monkeypatch.setattr(icc, "run_domain_onboarding", lambda *args, **kwargs: mutated)
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["icc_delta"]["runtime_gaps"]
    assert "persona runtime coverage rate" in report["block_reason"]
