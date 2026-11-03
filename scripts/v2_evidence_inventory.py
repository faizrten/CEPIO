"""Fail closed on unscored v2 evidence-inventory integrity.

Public PR references are leads only. This tool never awards or transfers points.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any

import yaml

DEFAULT_RUBRIC = Path("config/v2-scorecard-rubric.yaml")
DEFAULT_INVENTORY = Path("config/v2-evidence-inventory.yaml")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PUBLIC_PR_RE = re.compile(r"^PR #[1-9][0-9]*$")


class EvidenceInventoryError(ValueError):
    """Evidence inventory is structurally unsafe or makes premature scoring claims."""


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvidenceInventoryError(f"{path} must contain a mapping")
    return data


def validate_inventory(inventory: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if inventory.get("schema_version") != "2.0":
        raise EvidenceInventoryError("invalid inventory schema")
    if inventory.get("rubric_path") != str(DEFAULT_RUBRIC):
        raise EvidenceInventoryError("inventory must reference the candidate rubric")
    if inventory.get("legacy_scorecard_path") != "config/v1-scorecard.yaml":
        raise EvidenceInventoryError("inventory must preserve v1 canonical source")
    if inventory.get("governing_issue") != 326:
        raise EvidenceInventoryError("inventory must link governed cutover issue")
    if inventory.get("inventory_status") != "public_evidence_triage_only":
        raise EvidenceInventoryError("inventory may not claim qualification")
    if inventory.get("canonical_v2_score", "MISSING") is not None:
        raise EvidenceInventoryError("inventory must not assign a canonical v2 score")
    if inventory.get("earned_points_assessed") is not False:
        raise EvidenceInventoryError("inventory may not assert earned points")
    if rubric.get("canonical") is not False or rubric.get("status") != "proposed_unscored":
        raise EvidenceInventoryError("rubric is not the expected unscored candidate")

    snapshot = inventory.get("public_snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("branch") != "main":
        raise EvidenceInventoryError("inventory requires an explicit mainline snapshot")
    if not isinstance(snapshot.get("commit"), str) or not SHA_RE.fullmatch(snapshot["commit"]):
        raise EvidenceInventoryError("inventory requires exact pinned git SHA")
    if not isinstance(snapshot.get("source_scope"), str) or (
        "no protected" not in snapshot["source_scope"].lower()
    ):
        raise EvidenceInventoryError("scope must disclose that private proofs were not inspected")
    if not isinstance(inventory.get("limitations"), list) or len(inventory["limitations"]) < 4:
        raise EvidenceInventoryError("evidence limitations must be explicit")

    expected: dict[str, tuple[int, str]] = {}
    for dimension in rubric["dimensions"]:
        for gate in dimension["gates"]:
            expected[gate["id"]] = (gate["points"], gate["minimum_evidence_tier"])
    rows = inventory.get("gates")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise EvidenceInventoryError("inventory must cover exactly every candidate gate")
    seen: set[str] = set()
    count_refs = 0
    forbidden_keys = {"earned", "points_earned", "qualified", "awarded", "scored", "pass"}
    for row in rows:
        if not isinstance(row, dict):
            raise EvidenceInventoryError("inventory gate entry must be a mapping")
        gate_id = row.get("gate_id")
        if gate_id not in expected or gate_id in seen:
            raise EvidenceInventoryError("unknown or duplicate candidate gate")
        seen.add(gate_id)
        if row.get("scoring_status") != "not_assessed" or forbidden_keys.intersection(row):
            raise EvidenceInventoryError(f"gate {gate_id} attempts premature qualification")
        refs = row.get("candidate_public_refs")
        if not isinstance(refs, list) or len(set(refs)) != len(refs):
            raise EvidenceInventoryError(f"gate {gate_id} has invalid/duplicate refs")
        if any(not isinstance(ref, str) or not PUBLIC_PR_RE.fullmatch(ref) for ref in refs):
            raise EvidenceInventoryError(f"gate {gate_id} contains non-public/unsupported ref")
        count_refs += len(refs)
        for field in ("evidence_limitations", "next_qualification"):
            if not isinstance(row.get(field), str) or len(row[field]) < 35:
                raise EvidenceInventoryError(f"gate {gate_id} lacks {field}")
    if seen != set(expected):
        raise EvidenceInventoryError("candidate gate mapping incomplete")

    return {
        "inventory_status": "public_evidence_triage_only",
        "candidate_gates": len(expected),
        "candidate_public_refs": count_refs,
        "canonical_v2_score": None,
        "historical_v1_score": "69/100",
        "snapshot_commit": snapshot["commit"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--check", action="store_true", help="validate only")
    args = parser.parse_args()
    result = validate_inventory(_read(args.inventory), _read(args.rubric))
    print(
        f"v2 evidence triage valid: {result['candidate_gates']} unscored gates; "
        f"{result['candidate_public_refs']} candidate references; no points awarded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
