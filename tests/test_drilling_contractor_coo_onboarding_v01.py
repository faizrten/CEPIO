from pathlib import Path

from cepio.domain_onboarding import run_domain_onboarding
from cepio.icc_qualification import run_icc_persona_qualification


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/drilling-contractor-coo-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def test_drilling_contractor_coo_domain_onboarding_reaches_human_review():
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["current_state"] == "GENERALIZATION_REVIEW"
    assert report["domain"] == "drilling-contractor"
    assert report["semantic_baseline"]["semantic_check_pass_rate"] == 1.0
    assert report["runtime_qualification"]["runtime_coverage_rate"] == 1.0
    assert report["runtime_qualification"]["question_count"] == 8


def test_drilling_contractor_coo_icc_qualifies_composed_operating_contract_without_semantic_delta():
    report = run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["qualification_status"] == "QUALIFIED"
    assert report["domain"] == "drilling-contractor"
    assert report["persona_id"] == "chief-operating-officer"
    assert report["persona_binding"]["role"] == "Chief Operating Officer"
    assert report["persona_binding"]["selection_source"] == "explicit-persona-binding"
    assert report["persona_binding"]["binding_id"] == "drilling-contractor-coo-binding-v0.1"
    assert report["persona_binding"]["question_count"] == 8
    assert report["icc_delta"]["required_question_ids"] == [
        f"COO-{index:03d}" for index in range(1, 9)
    ]
    assert report["qualification"]["semantic_pass_rate"] == 1.0
    assert report["qualification"]["runtime_coverage_rate"] == 1.0
    assert len(report["icc_delta"]["required_capabilities"]) == 13
    assert len(report["icc_delta"]["reused_capabilities"]) == 13
    assert report["icc_delta"]["missing_capabilities"] == []
    assert report["icc_delta"]["new_semantic_candidates"] == []
    assert report["icc_delta"]["runtime_gaps"] == []
    assert report["icc_delta"]["policy_authority_gaps"] == []
    assert report["human_review_required"] is True
