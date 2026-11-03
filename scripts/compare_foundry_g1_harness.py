#!/usr/bin/env python3
"""Offline, fail-closed protocol comparison of two CEPIO Foundry G1 response artifacts.

No Azure SDK imports, network operations, model inference, credential handling or
claims of independently verified Decision persistence are performed here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from .run_foundry_reliability_g1 import G1_ALLOWED_TOOLS, qualify_payload
else:
    from run_foundry_reliability_g1 import G1_ALLOWED_TOOLS, qualify_payload

_ALLOWED = frozenset(G1_ALLOWED_TOOLS)


def _protocol_assessment(artifact: Any, *, role: str) -> dict[str, Any]:
    failures: list[str] = []
    if not isinstance(artifact, dict):
        return {
            "role": role,
            "protocol_pass": False,
            "live_g1_qualified": False,
            "failures": ["Artifact must be a JSON object"],
        }
    if artifact.get("gate") != "G1":
        failures.append("Artifact must identify G1 gate")
    if artifact.get("status") != "PASS":
        failures.append("Runner did not report protocol PASS")
    if artifact.get("failures") != []:
        failures.append("Runner failures must be an explicit empty list")
    if artifact.get("allowed_tools") != list(G1_ALLOWED_TOOLS):
        failures.append("Runner allowed_tools does not match frozen G1 allow-list")

    response = artifact.get("response")
    if not isinstance(response, dict):
        failures.append("Missing raw structured Foundry response")
    else:
        failures.extend(qualify_payload(response))
        calls = response.get("output")
        if isinstance(calls, list):
            for item in calls:
                if isinstance(item, dict) and item.get("type") == "mcp_call":
                    name = item.get("name")
                    if not isinstance(name, str) or name not in _ALLOWED:
                        failures.append(f"Unapproved MCP tool in response: {name!r}")

    return {
        "role": role,
        "agent": artifact.get("agent"),
        "subject_id": artifact.get("subject_id"),
        "artifact_declared_harness": artifact.get("harness"),
        "artifact_declared_model": artifact.get("model"),
        "protocol_pass": not failures,
        "live_g1_qualified": False,
        "failures": failures,
    }


def compare_artifacts(control: Any, candidate: Any) -> dict[str, Any]:
    """Compare source records only, never treat self-reported verification as trust."""
    baseline = _protocol_assessment(control, role="standard_foundry")
    experimental = _protocol_assessment(candidate, role="copilot_harness")

    confounders: list[str] = []
    if baseline["subject_id"] != experimental["subject_id"]:
        confounders.append("Subject IDs differ")
    if not baseline["subject_id"]:
        confounders.append("Subject ID is missing")
    if experimental["artifact_declared_harness"] != "microsoft_copilot_preview":
        confounders.append("Candidate artifact does not declare the expected preview harness")
    if not isinstance(control, dict) or not isinstance(candidate, dict):
        confounders.append("Malformed input artifacts")
    else:
        control_model = control.get("model")
        candidate_model = candidate.get("model")
        if not control_model or not candidate_model:
            confounders.append("Model identity/version not pinned in both artifacts")
        elif control_model != candidate_model:
            confounders.append("Model identities differ; harness-only attribution is invalid")

    protocol_ready = baseline["protocol_pass"] and experimental["protocol_pass"] and not confounders

    return {
        "schema_version": "1.0",
        "kind": "cepio-foundry-g1-harness-offline-protocol-comparison",
        "status": "PROTOCOL_COMPARABLE" if protocol_ready else "BLOCKED",
        "control": baseline,
        "candidate": experimental,
        "confounders": confounders,
        "live_g1_qualified": False,
        "decision_persistence_verified": False,
        "performance_uplift_established": False,
        "limitations": [
            "Untrusted saved Foundry response artifacts cannot independently prove actor identity or Decision persistence.",
            "A protocol comparison is not live G1, industrial-evaluation, deployment or product-release qualification.",
            "No performance uplift is established without protected expert evaluation, independently verified outcomes and measured cost/latency.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    control = json.loads(args.control.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    report = compare_artifacts(control, candidate)
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["status"] == "PROTOCOL_COMPARABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
