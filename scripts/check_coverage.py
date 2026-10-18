"""Deletion-aware coverage regression gate for CEPIO pull requests."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any


HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


@dataclass(frozen=True)
class FileCoverage:
    executed: frozenset[int]
    missing: frozenset[int]

    @property
    def executable(self) -> frozenset[int]:
        return self.executed | self.missing


@dataclass(frozen=True)
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int


def canonical_path(value: str) -> str:
    path = value.replace("\\", "/")
    marker = "src/cepio/"
    if marker in path:
        return marker + path.split(marker, 1)[1]
    if path.startswith("cepio/"):
        return f"src/{path}"
    return path.lstrip("./")


def load_coverage(path: str) -> tuple[dict[str, FileCoverage], dict[str, float | int]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    files = {
        canonical_path(name): FileCoverage(
            executed=frozenset(details.get("executed_lines", [])),
            missing=frozenset(details.get("missing_lines", [])),
        )
        for name, details in payload.get("files", {}).items()
    }
    totals = payload["totals"]
    statements = int(totals["num_statements"])
    covered = int(totals["covered_lines"])
    return files, {
        "num_statements": statements,
        "covered_lines": covered,
        "uncovered_lines": statements - covered,
        "percent_covered": float(totals["percent_covered"]),
    }


def parse_diff(base_ref: str) -> dict[str, list[Hunk]]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--unified=0",
            "--no-renames",
            f"{base_ref}...HEAD",
            "--",
            "src/cepio",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    changes: dict[str, list[Hunk]] = {}
    current: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("diff --git "):
            current = canonical_path(line.split()[3][2:])
            changes.setdefault(current, [])
            continue
        if current is None:
            continue
        match = HUNK_RE.match(line)
        if match:
            changes[current].append(
                Hunk(
                    old_start=int(match["old_start"]),
                    old_count=int(match["old_count"] or 1),
                    new_start=int(match["new_start"]),
                    new_count=int(match["new_count"] or 1),
                )
            )
    return changes


def changed_executable_lines(head: FileCoverage, hunks: list[Hunk]) -> frozenset[int]:
    changed: set[int] = set()
    executable = head.executable
    for hunk in hunks:
        changed.update(
            line
            for line in range(hunk.new_start, hunk.new_start + hunk.new_count)
            if line in executable
        )
    return frozenset(changed)


def evaluate(
    base_files: dict[str, FileCoverage],
    head_files: dict[str, FileCoverage],
    base_totals: dict[str, float | int],
    head_totals: dict[str, float | int],
    changes: dict[str, list[Hunk]],
    diff_threshold: float,
) -> dict[str, Any]:
    unchanged_regressions: dict[str, dict[str, int]] = {}
    for path in sorted(base_files.keys() & head_files.keys() - changes.keys()):
        before = len(base_files[path].missing)
        after = len(head_files[path].missing)
        if after > before:
            unchanged_regressions[path] = {
                "base_uncovered_lines": before,
                "head_uncovered_lines": after,
                "new_uncovered_lines": after - before,
            }

    changed_total = 0
    changed_covered = 0
    changed_files: dict[str, dict[str, float | int]] = {}
    for path, hunks in sorted(changes.items()):
        head = head_files.get(path)
        if head is None:
            continue
        lines = changed_executable_lines(head, hunks)
        covered = len(lines & head.executed)
        total = len(lines)
        changed_total += total
        changed_covered += covered
        changed_files[path] = {
            "executable_lines": total,
            "covered_lines": covered,
            "percent_covered": 100.0 if total == 0 else 100.0 * covered / total,
        }

    diff_percent = 100.0 if changed_total == 0 else 100.0 * changed_covered / changed_total
    uncovered_delta = int(head_totals["uncovered_lines"]) - int(base_totals["uncovered_lines"])
    passed = (
        uncovered_delta <= 0
        and not unchanged_regressions
        and diff_percent + 1e-9 >= diff_threshold
    )
    return {
        "base": base_totals,
        "head": head_totals,
        "aggregate_delta_percent": (
            float(head_totals["percent_covered"]) - float(base_totals["percent_covered"])
        ),
        "uncovered_line_delta": uncovered_delta,
        "changed_line_coverage": {
            "covered_lines": changed_covered,
            "executable_lines": changed_total,
            "percent_covered": diff_percent,
            "minimum_percent": diff_threshold,
        },
        "changed_files": changed_files,
        "unchanged_file_regressions": unchanged_regressions,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_coverage")
    parser.add_argument("head_coverage")
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--diff-threshold", type=float, default=90.0)
    parser.add_argument("--report", default="evidence/coverage-diff.json")
    args = parser.parse_args()

    base_files, base_totals = load_coverage(args.base_coverage)
    head_files, head_totals = load_coverage(args.head_coverage)
    result = evaluate(
        base_files,
        head_files,
        base_totals,
        head_totals,
        parse_diff(args.base_ref),
        args.diff_threshold,
    )

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    changed = result["changed_line_coverage"]
    print(
        "Coverage "
        f"base={base_totals['percent_covered']:.6f}% "
        f"head={head_totals['percent_covered']:.6f}% "
        f"delta={result['aggregate_delta_percent']:+.6f}pp; "
        f"uncovered lines delta={result['uncovered_line_delta']:+d}"
    )
    print(
        "Changed-line coverage "
        f"{changed['covered_lines']}/{changed['executable_lines']} "
        f"({changed['percent_covered']:.2f}%, minimum {changed['minimum_percent']:.2f}%)"
    )
    regressions = result["unchanged_file_regressions"]
    for path, details in regressions.items():
        print(
            f"Unchanged file coverage regression {path}: "
            f"{details['base_uncovered_lines']} -> {details['head_uncovered_lines']} uncovered lines"
        )

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
