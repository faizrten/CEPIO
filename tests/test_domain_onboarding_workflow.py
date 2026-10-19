from pathlib import Path

import pytest
import yaml

from cepio.domain_onboarding import (
    DomainOnboardingState,
    _artifact_path,
    _expected_gap_keys,
    _validate_gap_triage,
    load_domain_policy,
    load_domain_workflow,
    run_domain_onboarding,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/refinery-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"


def _write_yaml(path: Path, value: object) -> Path:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _gap_triage(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": "gap-test-v0.1",
        "version": "0.1",
        "archetype_id": "arch-v0.1",
        "competency_pack_id": "competency-v0.1",
        "status": "accepted",
        "decisions": [
            {
                "id": "GAP-001",
                "question_id": "Q-001",
                "disposition": "COMMON",
                "standards": ["STD-1"],
                "missing_semantics": ["urn:test:missing"],
            }
        ],
    }
    value.update(overrides)
    return value


def _validate(path: Path, expected: set[tuple[str, str]] | None = None) -> dict[str, object]:
    expected_gaps = {("Q-001", "urn:test:missing")} if expected is None else expected
    return _validate_gap_triage(
        path,
        expected=expected_gaps,
        archetype_id="arch-v0.1",
        competency_pack_id="competency-v0.1",
        question_ids={"Q-001"},
        standard_ids={"STD-1"},
        allowed_dispositions={"CORE", "COMMON", "DOMAIN", "MAPPING", "PROFILE", "REJECT"},
    )


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


def test_expected_gap_keys_only_includes_partial_and_fail():
    baseline = {
        "results": [
            {"id": "PASS", "status": "PASS", "missing": ["ignored"]},
            {"id": "PARTIAL", "status": "PARTIAL", "missing": ["a", "b"]},
            {"id": "FAIL", "status": "FAIL", "missing": ["c"]},
            {"id": "ERROR", "status": "ERROR", "missing": ["ignored-too"]},
        ]
    }
    assert _expected_gap_keys(baseline) == {
        ("PARTIAL", "a"),
        ("PARTIAL", "b"),
        ("FAIL", "c"),
    }


def test_artifact_path_is_repository_bounded(tmp_path: Path):
    artifact = tmp_path / "inside.yaml"
    artifact.write_text("id: inside\n", encoding="utf-8")
    assert _artifact_path(tmp_path, "inside.yaml") == artifact.resolve()

    with pytest.raises(ValueError, match="repository-relative"):
        _artifact_path(tmp_path, str(artifact.resolve()))
    with pytest.raises(ValueError, match="escapes repository root"):
        _artifact_path(tmp_path, "../outside.yaml")
    with pytest.raises(FileNotFoundError, match="required domain artifact not found"):
        _artifact_path(tmp_path, "missing.yaml")


def test_workflow_contract_rejects_undeclared_initial_state(tmp_path: Path):
    path = _write_yaml(
        tmp_path / "workflow.yaml",
        {
            "id": "workflow.test",
            "version": "0.1",
            "initial_state": "REQUESTED",
            "states": ["SCOPED", "BLOCKED"],
            "transitions": [],
        },
    )
    with pytest.raises(ValueError, match="initial_state"):
        load_domain_workflow(path)


def test_workflow_contract_rejects_undeclared_transition_state(tmp_path: Path):
    path = _write_yaml(
        tmp_path / "workflow.yaml",
        {
            "id": "workflow.test",
            "version": "0.1",
            "initial_state": "REQUESTED",
            "states": ["REQUESTED", "SCOPED", "BLOCKED"],
            "transitions": [
                {"source": "REQUESTED", "target": "BENCHMARKED", "gate": "invalid"}
            ],
        },
    )
    with pytest.raises(ValueError, match="undeclared state"):
        load_domain_workflow(path)


def test_policy_rejects_duplicate_gap_dispositions(tmp_path: Path):
    path = _write_yaml(
        tmp_path / "policy.yaml",
        {
            "id": "policy.test",
            "version": "0.1",
            "allowed_gap_dispositions": ["CORE", "CORE"],
        },
    )
    with pytest.raises(ValueError, match="must be unique"):
        load_domain_policy(path)


def test_gap_triage_accepts_exact_coverage_and_counts(tmp_path: Path):
    path = _write_yaml(tmp_path / "gaps.yaml", _gap_triage())
    result = _validate(path)
    assert result["decision_count"] == 1
    assert result["disposition_counts"]["COMMON"] == 1
    assert result["triage_id"] == "gap-test-v0.1"
    assert result["triage_version"] == "0.1"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"status": "draft"}, "must be accepted"),
        ({"archetype_id": "wrong"}, "archetype_id does not match"),
        ({"competency_pack_id": "wrong"}, "competency_pack_id does not match"),
        ({"decisions": "not-a-list"}, "decisions must be a list"),
        ({"decisions": ["not-a-mapping"]}, "each gap decision must be a mapping"),
        (
            {
                "decisions": [
                    {
                        "id": "GAP-001",
                        "question_id": "Q-001",
                        "disposition": "NOT_ALLOWED",
                        "missing_semantics": ["urn:test:missing"],
                    }
                ]
            },
            "unsupported gap disposition",
        ),
        (
            {
                "decisions": [
                    {
                        "id": "GAP-001",
                        "question_id": "Q-001",
                        "disposition": "COMMON",
                        "missing_semantics": [],
                    }
                ]
            },
            "must cover missing_semantics",
        ),
    ],
)
def test_gap_triage_rejects_invalid_structure(
    tmp_path: Path, overrides: dict[str, object], message: str
):
    path = _write_yaml(tmp_path / "gaps.yaml", _gap_triage(**overrides))
    with pytest.raises(ValueError, match=message):
        _validate(path)


def test_gap_triage_rejects_unknown_question(tmp_path: Path):
    triage = _gap_triage()
    decisions = triage["decisions"]
    assert isinstance(decisions, list)
    first = decisions[0]
    assert isinstance(first, dict)
    first["question_id"] = "UNKNOWN"
    path = _write_yaml(tmp_path / "gaps.yaml", triage)
    with pytest.raises(ValueError, match="unknown question ids"):
        _validate(path)


def test_gap_triage_rejects_unknown_standard(tmp_path: Path):
    triage = _gap_triage()
    decisions = triage["decisions"]
    assert isinstance(decisions, list)
    first = decisions[0]
    assert isinstance(first, dict)
    first["standards"] = ["UNKNOWN"]
    path = _write_yaml(tmp_path / "gaps.yaml", triage)
    with pytest.raises(ValueError, match="unknown standards ids"):
        _validate(path)


def test_gap_triage_rejects_duplicate_coverage(tmp_path: Path):
    triage = _gap_triage()
    decisions = triage["decisions"]
    assert isinstance(decisions, list)
    first = decisions[0]
    assert isinstance(first, dict)
    decisions.append(dict(first, id="GAP-002"))
    path = _write_yaml(tmp_path / "gaps.yaml", triage)
    with pytest.raises(ValueError, match="duplicate coverage"):
        _validate(path)


def test_gap_triage_rejects_untriaged_current_gap(tmp_path: Path):
    path = _write_yaml(tmp_path / "gaps.yaml", _gap_triage(decisions=[]))
    with pytest.raises(ValueError, match="current semantic gaps are not triaged"):
        _validate(path)


def test_gap_triage_rejects_stale_coverage(tmp_path: Path):
    path = _write_yaml(tmp_path / "gaps.yaml", _gap_triage())
    with pytest.raises(ValueError, match="stale/non-current gaps"):
        _validate(path, expected=set())
