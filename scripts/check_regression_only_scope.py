"""Fail-closed routing for the first CEPIO cross-domain regression-only PR.

This is a narrow policy exception to *new domain onboarding*, not an exemption
from CI, independent regression qualification, source rights, or promotion review.
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

REGRESSION_MANIFEST = "generalization/regression/evidence-decision-reassessment-v0.1.yaml"
REGRESSION_TEST = "tests/test_evidence_decision_reassessment_v01.py"

# Deliberately exact paths: this version does not authorize arbitrary test,
# source, workflow, domain-pack or policy changes to evade onboarding review.
ALLOWED_PATHS = frozenset(
    {
        REGRESSION_MANIFEST,
        REGRESSION_TEST,
        "tests/test_regression_only_scope_v01.py",
        "scripts/check_regression_only_scope.py",
        "docs/evidence-decision-cross-domain-v0.1.md",
        ".github/workflows/domain-onboarding.yml",
    }
)


def eligible_regression_only(changes: Sequence[tuple[str, str]]) -> bool:
    """Require one known regression and its test; deny removes/renames/mixed scope."""
    if not changes:
        return False
    by_path: dict[str, str] = {}
    for status, path in changes:
        if status not in {"A", "M"} or path not in ALLOWED_PATHS:
            return False
        if path in by_path:
            return False
        by_path[path] = status
    return REGRESSION_MANIFEST in by_path and REGRESSION_TEST in by_path


def read_changes(base_sha: str, head_sha: str) -> list[tuple[str, str]]:
    """Read GitHub's checked-out pull-request diff; preserve explicit status."""
    result = subprocess.run(
        ["git", "diff", "--no-renames", "--name-status", base_sha, head_sha, "--"],
        check=True,
        text=True,
        capture_output=True,
    )
    changes: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 2:
            raise ValueError(f"Unexpected git diff status record: {line!r}")
        changes.append((fields[0], fields[1]))
    return changes


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise ValueError("Usage: check_regression_only_scope.py BASE_SHA HEAD_SHA")
    changes = read_changes(argv[0], argv[1])
    accepted = eligible_regression_only(changes)
    if accepted:
        print("Qualified file-scope routing: evidence-decision regression-only")
        return 0
    print(
        "Not eligible for regression-only mode: missing designated files, "
        "unexpected paths, removals/renames, or duplicate paths."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
