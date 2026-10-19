from pathlib import Path

from cepio.domain_onboarding import (
    DomainOnboardingState,
    load_domain_policy,
    load_domain_workflow,
    run_domain_onboarding,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/refinery-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def test_refinery_reference_pack_reaches_generalization_review():
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["current_state"] == DomainOnboardingState.GENERALIZATION_REVIEW.value
    assert report["domain"] == "refinery-process-manufacturing"
    assert report["domain_delta"]["semantic_pass_rate"] == 1.0
    assert report["domain_delta"]["semantic_gap_count"] == 0
    assert report["domain_delta"]["runtime_coverage_rate"] == 1.0
    assert report["human_review_required"] is True
    assert [item["to"] for item in report["timeline"]] == [
        "SCOPED",
        "BENCHMARKED",
        "BASELINED",
        "GAP_ANALYZED",
        "QUALIFYING",
        "QUALIFIED",
        "GENERALIZATION_REVIEW",
    ]


def test_domain_policy_has_common_classification_and_human_release_gates():
    policy = load_domain_policy(POLICY)
    workflow = load_domain_workflow(WORKFLOW)

    assert "COMMON" in policy.allowed_gap_dispositions
    assert DomainOnboardingState.GENERALIZATION_REVIEW in policy.human_review_states
    assert DomainOnboardingState.RELEASE_CANDIDATE in policy.human_review_states
    assert any(
        transition.source == DomainOnboardingState.GENERALIZATION_REVIEW
        and transition.target == DomainOnboardingState.RELEASE_CANDIDATE
        and transition.gate == "generalization_approved"
        for transition in workflow.transitions
    )
    assert any(
        transition.source == DomainOnboardingState.RELEASE_CANDIDATE
        and transition.target == DomainOnboardingState.RELEASED
        and transition.gate == "release_approved"
        for transition in workflow.transitions
    )
