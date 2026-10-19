from pathlib import Path

import pytest
import yaml

import cepio.domain_onboarding as domain_onboarding
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


def _manifest_copy(tmp_path: Path, **artifact_overrides: object) -> Path:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    payload["artifacts"].update(artifact_overrides)
    return _write_yaml(tmp_path / "manifest.yaml", payload)


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


def test_yaml_loader_requires_mapping(tmp_path: Path):
    path = tmp_path / "invalid.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        domain_onboarding._load_yaml(path)


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
            "transitions": [{"source": "REQUESTED", "target": "BENCHMARKED", "gate": "invalid"}],
        },
    )
    with pytest.raises(ValueError, match="undeclared state"):
        load_domain_workflow(path)


def test_runtime_rejects_transition_missing_from_contract(tmp_path: Path):
    payload = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    payload["transitions"] = [
        item
        for item in payload["transitions"]
        if not (item["source"] == "REQUESTED" and item["target"] == "SCOPED")
    ]
    path = _write_yaml(tmp_path / "workflow.yaml", payload)
    with pytest.raises(ValueError, match="workflow forbids transition REQUESTED->SCOPED"):
        run_domain_onboarding(ROOT, MANIFEST, path, POLICY)


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


def test_onboarding_blocks_scope_loader_errors(monkeypatch: pytest.MonkeyPatch):
    def fail_load(path: Path) -> object:
        raise RuntimeError(f"cannot load {path.name}")

    monkeypatch.setattr(domain_onboarding, "load_archetype", fail_load)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "cannot load" in report["block_reason"]


def test_onboarding_blocks_mismatched_archetype(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.load_archetype

    def mismatch(path: Path) -> object:
        return original(path).model_copy(update={"id": "different-archetype"})

    monkeypatch.setattr(domain_onboarding, "load_archetype", mismatch)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "competency archetype" in report["block_reason"]


def test_onboarding_blocks_empty_persona_pack(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.load_personas

    def empty(path: Path) -> object:
        return original(path).model_copy(update={"personas": []})

    monkeypatch.setattr(domain_onboarding, "load_personas", empty)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "persona pack must contain at least one persona"


def test_onboarding_blocks_empty_standards_registry(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.load_standards

    def empty(path: Path) -> object:
        return original(path).model_copy(update={"references": []})

    monkeypatch.setattr(domain_onboarding, "load_standards", empty)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "standards registry must contain at least one reference"


def test_onboarding_blocks_unfrozen_benchmark(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.load_pack

    def unfrozen(path: Path) -> object:
        return original(path).model_copy(update={"frozen": False})

    monkeypatch.setattr(domain_onboarding, "load_pack", unfrozen)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "must be frozen" in report["block_reason"]


def test_onboarding_blocks_baseline_execution_error(monkeypatch: pytest.MonkeyPatch):
    def fail_harness(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("baseline exploded")

    monkeypatch.setattr(domain_onboarding, "run_harness", fail_harness)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "baseline exploded"


def test_onboarding_blocks_when_gap_triage_is_required(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.run_harness

    def with_gap(*args: object, **kwargs: object) -> dict[str, object]:
        report = original(*args, **kwargs)
        report["results"][0]["status"] = "PARTIAL"
        report["results"][0]["missing"] = ["urn:test:new-gap"]
        return report

    monkeypatch.setattr(domain_onboarding, "run_harness", with_gap)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "require an accepted triage pack" in report["block_reason"]


def test_onboarding_blocks_gap_triage_validation_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    original = domain_onboarding.run_harness

    def with_gap(*args: object, **kwargs: object) -> dict[str, object]:
        report = original(*args, **kwargs)
        report["results"][0]["status"] = "PARTIAL"
        report["results"][0]["missing"] = ["urn:test:new-gap"]
        return report

    def fail_triage(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("triage rejected")

    manifest = _manifest_copy(
        tmp_path, gap_triage="generalization/gaps/drilling-contractor-v0.1.yaml"
    )
    monkeypatch.setattr(domain_onboarding, "run_harness", with_gap)
    monkeypatch.setattr(domain_onboarding, "_validate_gap_triage", fail_triage)
    report = run_domain_onboarding(ROOT, manifest, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "triage rejected"


def test_onboarding_blocks_critical_and_error_semantic_results(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.run_harness

    def failing_semantics(*args: object, **kwargs: object) -> dict[str, object]:
        report = original(*args, **kwargs)
        report["results"][0]["status"] = "FAIL"
        report["results"][0]["missing"] = []
        report["status_counts"]["ERROR"] = 1
        return report

    monkeypatch.setattr(domain_onboarding, "run_harness", failing_semantics)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "critical failures" in report["block_reason"]
    assert "ERROR" in report["block_reason"]


def test_onboarding_blocks_when_runtime_qualification_errors(monkeypatch: pytest.MonkeyPatch):
    def fail_runtime(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("runtime fixture failed")

    monkeypatch.setattr(domain_onboarding, "run_runtime_coverage", fail_runtime)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "runtime fixture failed"


def test_onboarding_blocks_runtime_threshold_and_failed_results(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.run_runtime_coverage

    def degraded_runtime(*args: object, **kwargs: object) -> dict[str, object]:
        report = original(*args, **kwargs)
        report["runtime_coverage_rate"] = 0.5
        report["status_counts"]["FAIL"] = 1
        report["status_counts"]["ERROR"] = 1
        return report

    monkeypatch.setattr(domain_onboarding, "run_runtime_coverage", degraded_runtime)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "runtime coverage rate 0.500" in report["block_reason"]
    assert "FAIL/ERROR" in report["block_reason"]


def test_onboarding_blocks_when_required_runtime_suite_is_missing(tmp_path: Path):
    manifest = _manifest_copy(tmp_path, runtime_suite=None)
    report = run_domain_onboarding(ROOT, manifest, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "policy requires a runtime qualification suite"


def test_onboarding_blocks_when_semantic_threshold_regresses(monkeypatch: pytest.MonkeyPatch):
    original = domain_onboarding.run_harness

    def lower_rate(*args: object, **kwargs: object) -> dict[str, object]:
        report = original(*args, **kwargs)
        report["semantic_check_pass_rate"] = 0.5
        return report

    monkeypatch.setattr(domain_onboarding, "run_harness", lower_rate)
    report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    assert report["status"] == "BLOCKED"
    assert "semantic pass rate 0.500" in report["block_reason"]
