#!/usr/bin/env python3
"""Run CEPIO deterministic operational assurance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.operational_assurance import run_operational_assurance


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEPIO deterministic operational-assurance harness")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-gap", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    scenario = args.scenario or root / "generalization/runtime/drilling-contractor-operational-assurance-v0.4.yaml"
    report = run_operational_assurance(root, scenario)

    print(f"CEPIO Operational Assurance v{report['assurance_version']}")
    print(f"mode: {report['mode']}")
    print(f"archetype: {report['archetype_id']}")
    print(f"scenario: {report['scenario_id']}")
    print(f"scenario hash: {report['scenario_hash'][:16]}")
    print(f"competency pack: {report['competency_pack']}")
    print(f"gates: {report['gate_count']}")
    print(f"status: {report['status_counts']}")
    print(f"operational assurance: {report['assurance_pass_rate']:.1%}")
    for result in report["results"]:
        print(f"{result['question_id']} {result['dimension']} {result['status']} | {result['check']}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.fail_on_gap and report["status_counts"]["PASS"] != report["gate_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
