from pathlib import Path

from cepio.domain_onboarding import run_domain_onboarding
from cepio.icc_qualification import run_icc_persona_qualification


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT / "generalization/domain-packs/drilling-contractor-maintenance-planner-reference-v0.1.yaml"
)
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def test_drilling_contractor_maintenance_planner_reuses_frozen_domain_pack():
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["current_state"] == "GENERALIZATION_REVIEW"
    assert report["domain"] == "drilling-contractor"
    assert report["semantic_baseline"]["semantic_check_pass_rate"] == 1.0
    assert report["runtime_qualification"]["runtime_coverage_rate"] == 1.0
    assert report["runtime_qualification"]["question_count"] == 14


def test_drilling_contractor_maintenance_planner_icc_is_binding_only_reuse():
    report = run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["qualification_status"] == "QUALIFIED"
    assert report["domain"] == "drilling-contractor"
    assert report["persona_id"] == "maintenance-planner"
    assert report["persona_binding"]["role"] == "Maintenance Planner"
    assert report["persona_binding"]["selection_source"] == "explicit-persona-binding"
    assert (
        report["persona_binding"]["binding_id"]
        == "drilling-contractor-maintenance-planner-binding-v0.1"
    )
    assert report["persona_binding"]["question_count"] == 6
    assert report["icc_delta"]["required_question_ids"] == [
        "DC-PC-005",
        "DC-PC-006",
        "DC-PC-008",
        "DC-PC-012",
        "DC-PC-013",
        "DC-PC-014",
    ]
    assert report["qualification"]["semantic_pass_rate"] == 1.0
    assert report["qualification"]["runtime_coverage_rate"] == 1.0
    assert report["icc_delta"]["required_capabilities"]
    assert len(report["icc_delta"]["reused_capabilities"]) == len(
        report["icc_delta"]["required_capabilities"]
    )
    assert report["icc_delta"]["missing_capabilities"] == []
    assert report["icc_delta"]["new_semantic_candidates"] == []
    assert report["icc_delta"]["runtime_gaps"] == []
    assert report["icc_delta"]["policy_authority_gaps"] == []
    assert report["human_review_required"] is True
