#!/usr/bin/env python3
"""Run the CEPIO Generalization & Competency Harness v0.1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.generalization import run_harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEPIO deterministic semantic-readiness harness")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--archetype", type=Path)
    parser.add_argument("--competency", type=Path)
    parser.add_argument("--personas", type=Path)
    parser.add_argument("--standards", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-critical-gap", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    base = root / "generalization"
    report = run_harness(
        root,
        args.archetype or base / "archetypes/drilling-contractor-v0.1.yaml",
        args.competency or base / "competency/drilling-contractor-v0.1.yaml",
        args.personas or base / "personas/drilling-contractor-v0.1.yaml",
        args.standards or base / "standards/drilling-references.yaml",
    )

    print(f"CEPIO Generalization Harness v{report['harness_version']}")
    print(f"mode: {report['mode']}")
    print(f"archetype: {report['archetype_id']}")
    print(f"batch: {report['batch_hash'][:16]}")
    print(f"ontology: {report['ontology_hash'][:16]}")
    print(f"questions: {report['question_count']}")
    print(f"status: {report['status_counts']}")
    print(f"semantic checks: {report['semantic_check_pass_rate']:.1%}")
    for result in report["results"]:
        suffix = ""
        if result["missing"]:
            suffix = " | missing: " + "; ".join(result["missing"])
        if result["runtime_status"] == "NOT_RUN":
            suffix += " | runtime: NOT_RUN"
        print(f"{result['id']} {result['status']} {result['checks_passed']}/{result['checks_total']}{suffix}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.fail_on_critical_gap:
        critical_gap = any(
            result["priority"] == "critical" and result["status"] != "PASS"
            for result in report["results"]
        )
        if critical_gap:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
