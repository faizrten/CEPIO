import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_compounding_intelligence import (  # noqa: E402
    HumanDecisionPack,
    ReleaseDecision,
    _repo_artifact,
    _release_gate,
    _validate_promotion_workflow,
    discover_promotion_drafts,
    run_cross_domain_regression,
    run_cycle,
)


DOMAIN_MANIFEST = ROOT / "generalization/domain-packs/refinery-reference-v0.1.yaml"
DOMAIN_WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
DOMAIN_POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"
REGISTRY = ROOT / "generalization/capabilities/registry-v0.1.yaml"
REGRESSION = ROOT / "generalization/regression/industrial-common-v0.1.yaml"
PROMOTION_POLICY = ROOT / "policies/capability-promotion-v0.1.yaml"
PROMOTION_WORKFLOW = ROOT / "workflows/capability-promotion-v0.1.yaml"


def _cycle(**overrides: Path | None):
    values: dict[str, Path | None] = {
        "onboarding_report_path": None,
        "promotion_pack_path": None,
        "promotion_decisions_path": None,
        "release_decision_path": None,
    }
    values.update(overrides)
    return run_cycle(
        ROOT,
        domain_manifest_path=DOMAIN_MANIFEST,
        domain_workflow_path=DOMAIN_WORKFLOW,
        domain_policy_path=DOMAIN_POLICY,
        registry_path=REGISTRY,
        regression_suite_path=REGRESSION,
        promotion_policy_path=PROMOTION_POLICY,
        promotion_workflow_path=PROMOTION_WORKFLOW,
        onboarding_report_path=values["onboarding_report_path"],
        promotion_pack_path=values["promotion_pack_path"],
        promotion_decisions_path=values["promotion_decisions_path"],
        release_decision_path=values["release_decision_path"],
    )


def test_cross_domain_regression_survives_drilling_and_refinery():
    report = run_cross_domain_regression(ROOT, REGRESSION)
    assert report["target_count"] == 2
    assert report["passed_targets"] == 2
    assert report["failed_targets"] == 0
    assert report["survival_rate"] == 1.0
    assert {item["domain"] for item in report["results"]} == {
        "drilling-contractor",
        "refinery-process-manufacturing",
    }


def test_refinery_compounding_canary_reaches_release_review():
    report = _cycle()
    assert report["status"] == "READY_FOR_RELEASE_REVIEW"
    assert report["state"] == "RELEASE_REVIEW"
    assert report["domain"] == "refinery-process-manufacturing"
    assert report["regression"]["survival_rate"] == 1.0
    assert report["promotion_drafts"] == []
    assert report["promotions_applied"] == 0
    assert report["human_release_approval_required"] is True
    metrics = report["registry_metrics_after"]
    assert metrics["capability_count"] == 1
    assert metrics["cross_domain_capability_count"] == 1
    assert metrics["regression_survival_rate"] == 1.0
    assert metrics["reusable_competency_coverage_rate"] == pytest.approx(0.2)
    assert metrics["marginal_gap_rate"] == 0.0


def test_human_release_decision_can_complete_cycle(tmp_path: Path):
    release = tmp_path / "release.yaml"
    release.write_text(
        yaml.safe_dump(
            {
                "id": "release-refinery-v0.1",
                "domain": "refinery-process-manufacturing",
                "decision": "APPROVE",
                "actor_role": "industry-architecture-owner",
                "rationale": "Qualified evidence and regression reviewed.",
            }
        ),
        encoding="utf-8",
    )
    report = _cycle(release_decision_path=release)
    assert report["status"] == "RELEASED"
    assert report["state"] == "DOMAIN_RELEASED"
    assert report["human_release_approval_required"] is False


def test_release_decision_cannot_be_granted_by_ai_role():
    with pytest.raises(ValidationError, match="cannot approve domain release"):
        ReleaseDecision.model_validate(
            {
                "id": "bad",
                "domain": "refinery-process-manufacturing",
                "decision": "APPROVE",
                "actor_role": "ai_agent",
                "rationale": "not allowed",
            }
        )


def test_release_gate_fails_closed():
    released, blockers, waiting = _release_gate(
        domain="refinery",
        onboarding_status="BLOCKED",
        regression_survival_rate=0.5,
        unresolved_drafts=2,
        promotion_blockers=["promotion blocked"],
        release_decision=None,
    )
    assert released is False
    assert waiting is False
    assert len(blockers) == 4


def test_refinery_has_no_unresolved_promotion_drafts():
    assert discover_promotion_drafts(ROOT, DOMAIN_MANIFEST) == []


def test_promotion_workflow_contract_is_complete():
    assert _validate_promotion_workflow(PROMOTION_WORKFLOW) == "workflow.capability-promotion.v1"


def test_compounding_artifacts_are_repository_bounded(tmp_path: Path):
    assert _repo_artifact(ROOT, "generalization/capabilities/registry-v0.1.yaml") == (
        REGISTRY.resolve()
    )
    with pytest.raises(ValueError, match="repository-relative"):
        _repo_artifact(ROOT, str(REGISTRY.resolve()))
    with pytest.raises(ValueError, match="escapes repository root"):
        _repo_artifact(ROOT, "../escape.yaml")
    with pytest.raises(FileNotFoundError, match="required compounding artifact"):
        _repo_artifact(ROOT, "generalization/capabilities/missing.yaml")


def test_human_decision_pack_rejects_duplicate_subjects():
    with pytest.raises(ValidationError, match="duplicate promotion subjects"):
        HumanDecisionPack.model_validate(
            {
                "id": "decisions",
                "version": "0.1",
                "decisions": [
                    {
                        "id": "d1",
                        "subject_id": "same",
                        "decision": "APPROVE",
                        "actor_role": "architect",
                        "rationale": "one",
                    },
                    {
                        "id": "d2",
                        "subject_id": "same",
                        "decision": "REJECT",
                        "actor_role": "architect",
                        "rationale": "two",
                    },
                ],
            }
        )
