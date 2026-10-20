from pathlib import Path

from cepio.domain_onboarding import (
    DomainOnboardingState,
    load_domain_manifest,
    run_domain_onboarding,
)
from cepio.generalization import load_personas


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/drilling-contractor-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def test_drilling_contractor_reference_onboards_rig_manager():
    manifest = load_domain_manifest(MANIFEST)
    personas = load_personas(ROOT / manifest.artifacts.personas)

    assert manifest.domain == "drilling-contractor"
    assert "rig-manager" in {persona.id for persona in personas.personas}

    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["current_state"] == DomainOnboardingState.GENERALIZATION_REVIEW.value
    assert report["domain"] == "drilling-contractor"
    assert report["domain_delta"]["semantic_pass_rate"] == 1.0
    assert report["domain_delta"]["semantic_gap_count"] == 0
    assert report["domain_delta"]["runtime_coverage_rate"] == 1.0
    assert report["human_review_required"] is True
    assert report["runtime_qualification"]["status_counts"]["FAIL"] == 0
    assert report["runtime_qualification"]["status_counts"]["ERROR"] == 0
    assert [item["to"] for item in report["timeline"]] == [
        "SCOPED",
        "BENCHMARKED",
        "BASELINED",
        "GAP_ANALYZED",
        "QUALIFYING",
        "QUALIFIED",
        "GENERALIZATION_REVIEW",
    ]
