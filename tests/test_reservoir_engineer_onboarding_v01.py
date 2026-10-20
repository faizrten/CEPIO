from pathlib import Path

from cepio.domain_onboarding import run_domain_onboarding
from cepio.icc_qualification import run_icc_persona_qualification


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/subsurface-reservoir-engineering-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def test_reservoir_engineering_domain_onboarding_reaches_human_review():
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["current_state"] == "GENERALIZATION_REVIEW"
    assert report["domain"] == "subsurface-reservoir-engineering"
    assert report["semantic_baseline"]["semantic_check_pass_rate"] == 1.0
    assert report["runtime_qualification"]["runtime_coverage_rate"] == 1.0
    assert report["runtime_qualification"]["question_count"] == 8


def test_reservoir_engineer_icc_qualifies_all_frozen_questions_without_semantic_delta():
    report = run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["qualification_status"] == "QUALIFIED"
    assert report["domain"] == "subsurface-reservoir-engineering"
    assert report["persona_id"] == "reservoir-engineer"
    assert report["persona_binding"]["role"] == "Reservoir Engineer"
    assert report["persona_binding"]["selection_source"] == "explicit-persona-binding"
    assert report["persona_binding"]["binding_id"] == "subsurface-reservoir-engineer-binding-v0.1"
    assert report["persona_binding"]["question_count"] == 8
    assert report["icc_delta"]["required_question_ids"] == [f"RE-{index:03d}" for index in range(1, 9)]
    assert report["qualification"]["semantic_pass_rate"] == 1.0
    assert report["qualification"]["runtime_coverage_rate"] == 1.0
    assert report["icc_delta"]["required_capabilities"]
    assert len(report["icc_delta"]["reused_capabilities"]) == len(report["icc_delta"]["required_capabilities"])
    assert report["icc_delta"]["missing_capabilities"] == []
    assert report["icc_delta"]["new_semantic_candidates"] == []
    assert report["icc_delta"]["runtime_gaps"] == []
    assert report["icc_delta"]["policy_authority_gaps"] == []
    assert report["human_review_required"] is True
