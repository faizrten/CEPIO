#!/usr/bin/env python3
"""Execute the CEPIO Domain Onboarding control-plane workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.domain_onboarding import run_domain_onboarding


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the governed CEPIO Domain Onboarding workflow"
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("generalization/domain-packs/refinery-reference-v0.1.yaml"),
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        default=Path("workflows/domain-onboarding-v0.1.yaml"),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("policies/domain-onboarding-v0.1.yaml"),
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    workflow = args.workflow if args.workflow.is_absolute() else root / args.workflow
    policy = args.policy if args.policy.is_absolute() else root / args.policy

    report = run_domain_onboarding(root, manifest, workflow, policy)

    print(f"CEPIO Domain Onboarding {report['workflow_version']}")
    print(f"domain: {report['domain']}")
    print(f"state: {report['current_state']}")
    print(f"status: {report['status']}")
    for event in report["timeline"]:
        print(f"  {event['from']} -> {event['to']} [{event['gate']}]")

    delta = report.get("domain_delta")
    if delta:
        print(f"semantic pass rate: {delta['semantic_pass_rate']:.1%}")
        runtime_rate = delta.get("runtime_coverage_rate")
        if runtime_rate is not None:
            print(f"runtime coverage: {runtime_rate:.1%}")
        print(f"semantic gaps: {delta['semantic_gap_count']}")
        print(f"gap dispositions: {delta['gap_disposition_counts']}")

    if report["status"] == "BLOCKED":
        print(f"blocked: {report['block_reason']}")
    print(f"next: {report['next_action']}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    if args.fail_on_blocked and report["status"] == "BLOCKED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
