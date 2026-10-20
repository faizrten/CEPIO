#!/usr/bin/env python3
"""Execute persona-scoped CEPIO Industrial Capability Contract qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.icc_qualification import run_icc_persona_qualification


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run persona-scoped CEPIO Industrial Capability Contract qualification"
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--persona-id")
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

    report = run_icc_persona_qualification(
        root,
        manifest,
        workflow,
        policy,
        persona_id=args.persona_id,
    )

    print(f"CEPIO ICC Persona Qualification {report['contract_version']}")
    print(f"domain: {report['domain']}")
    print(f"persona: {report.get('persona_id')}")
    print(f"state: {report['current_state']}")
    print(f"status: {report['status']}")

    qualification = report.get("qualification")
    if qualification:
        print(f"semantic pass rate: {qualification['semantic_pass_rate']:.1%}")
        print(f"runtime coverage: {qualification['runtime_coverage_rate']:.1%}")

    delta = report.get("icc_delta")
    if delta:
        print(f"required capabilities: {len(delta['required_capabilities'])}")
        print(f"reused capabilities: {len(delta['reused_capabilities'])}")
        print(f"missing capabilities: {len(delta['missing_capabilities'])}")
        print(f"semantic candidates: {len(delta['new_semantic_candidates'])}")
        print(f"runtime gaps: {len(delta['runtime_gaps'])}")
        print(f"policy/authority gaps: {len(delta['policy_authority_gaps'])}")

    if report["status"] == "BLOCKED":
        print(f"blocked: {report['block_reason']}")
    print(f"next: {report.get('next_action', '')}")

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
