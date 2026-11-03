"""Regression-only governance routing must not weaken domain onboarding."""

from pathlib import Path
from runpy import run_path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = run_path(str(ROOT / "scripts/check_regression_only_scope.py"))
ALLOWED_PATHS = POLICY["ALLOWED_PATHS"]
REGRESSION_MANIFEST = POLICY["REGRESSION_MANIFEST"]
REGRESSION_TEST = POLICY["REGRESSION_TEST"]
eligible_regression_only = POLICY["eligible_regression_only"]


def test_explicit_regression_with_designated_test_is_allowed():
    assert eligible_regression_only(
        [
            ("A", REGRESSION_MANIFEST),
            ("A", REGRESSION_TEST),
            ("M", ".github/workflows/domain-onboarding.yml"),
            ("A", "scripts/check_regression_only_scope.py"),
            ("A", "tests/test_regression_only_scope_v01.py"),
            ("A", "docs/evidence-decision-cross-domain-v0.1.md"),
        ]
    )


def test_requires_manifest_and_the_specific_regression_test():
    assert not eligible_regression_only([("A", REGRESSION_MANIFEST)])
    assert not eligible_regression_only([("A", REGRESSION_TEST)])
    assert not eligible_regression_only([])


def test_deny_mixed_scope_with_domain_ontology_runtime_or_ci_changes():
    for forbidden in (
        "generalization/domain-packs/subsurface-reference.yaml",
        "generalization/competency/refinery-example.yaml",
        "generalization/runtime/refinery-example.yaml",
        "ontologies/core.ttl",
        "src/cepio/policy.py",
        ".github/workflows/governance.yml",
        "tests/test_runtime_coverage.py",
        "generalization/regression/other-regression-v0.1.yaml",
        "scripts/unrelated.py",
    ):
        assert not eligible_regression_only(
            [("A", REGRESSION_MANIFEST), ("A", REGRESSION_TEST), ("M", forbidden)]
        )


def test_removals_renames_unknown_status_and_duplicate_paths_fail_closed():
    for invalid_status in ("D", "R100", "C100", "T", "U", "??"):
        assert not eligible_regression_only(
            [
                (invalid_status, REGRESSION_MANIFEST),
                ("A", REGRESSION_TEST),
            ]
        )
    assert not eligible_regression_only(
        [
            ("A", REGRESSION_MANIFEST),
            ("A", REGRESSION_TEST),
            ("M", REGRESSION_TEST),
        ]
    )


def test_regression_exception_cannot_expand_silently():
    assert ALLOWED_PATHS == {
        REGRESSION_MANIFEST,
        REGRESSION_TEST,
        "tests/test_regression_only_scope_v01.py",
        "scripts/check_regression_only_scope.py",
        "docs/evidence-decision-cross-domain-v0.1.md",
        "docs/adr/ADR-0048-cross-domain-regression-only-qualification.md",
        ".github/workflows/domain-onboarding.yml",
    }


def test_workflow_preserves_onboarding_and_requires_deterministic_regression():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/domain-onboarding.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["domain-onboarding"]["steps"]
    commands = {step.get("name"): step for step in steps if "name" in step}
    resolver = commands["Resolve explicit onboarding target"]["run"]
    assert "scripts/check_regression_only_scope.py" in resolver
    assert "DOMAIN_QUALIFICATION_MODE=regression" in resolver

    for name in (
        "Run governed Domain Onboarding workflow",
        "Run persona-scoped ICC qualification",
        "Run compounding industrial-intelligence loop",
        "Run Domain Onboarding, ICC and compounding contract tests",
    ):
        assert "regression" in commands[name]["if"]

    qualification = commands["Qualify cross-domain regression-only"]["run"]
    assert "tests/test_evidence_decision_reassessment_v01.py" in qualification
    assert "tests/test_regression_only_scope_v01.py" in qualification
    assert "industrial-common-v0.1.yaml" in qualification
