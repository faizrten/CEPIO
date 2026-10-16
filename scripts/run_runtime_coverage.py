#!/usr/bin/env python3
"""Run CEPIO deterministic runtime-evidence coverage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.runtime_coverage import run_runtime_coverage


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEPIO deterministic runtime-evidence coverage")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--suite", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-gap", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    suite = args.suite or root / "generalization/runtime/drilling-contractor-runtime-coverage-v0.5.yaml"
    report = run_runtime_coverage(root, suite)

    print(f"CEPIO Runtime Coverage v{report['runtime_coverage_version']}")
    print(f"mode: {report['mode']}")
    print(f"archetype: {report['archetype_id']}")
    print(f"suite: {report['suite_id']}")
    print(f"suite hash: {report['suite_hash'][:16]}")
    print(f"competency pack: {report['competency_pack']}")
    print(f"questions: {report['question_count']}")
    print(f"status: {report['status_counts']}")
    print(f"runtime coverage: {report['runtime_coverage_rate']:.1%}")
    for result in report["results"]:
        print(
            f"{result['question_id']} {result['status']} "
            f"| probes={result['probe_count']} "
            f"| evidence={result['operator_evidence_gate']['passed']}"
        )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.fail_on_gap and report["status_counts"]["PASS"] != report["question_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
