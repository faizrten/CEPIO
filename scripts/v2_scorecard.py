from __future__ import annotations

"""Validate the unscored CEPIO v2 candidate rubric and historical crosswalk.

This deliberately does NOT calculate or publish a v2 maturity percentage.
The canonical v1 evidence-based score is governed separately until migration.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

RUBRIC = Path("config/v2-scorecard-rubric.yaml")
CROSSWALK = Path("config/v2-scorecard-crosswalk.yaml")
LEGACY = Path("config/v1-scorecard.yaml")
WEIGHTS = {
    "CORE": 10,
    "IQ": 25,
    "ASSURANCE": 20,
    "INTEGRATION": 15,
    "COMPOUND": 10,
    "PRODUCTION": 10,
    "PROFESSIONAL": 10,
}
EVIDENCE_TIERS = (
    "synthetic_conformance",
    "independent_offline",
    "live_source",
    "field_validated",
)
BASELINE_SHA = "a179e9cfc0dbf5e866a6a6aa143eb4290e79918d"


class RubricError(ValueError):
    """A proposed-rubric or crosswalk governance contract is violated."""


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RubricError(f"{path}: expected a mapping")
    return data


def validate(
    rubric: dict[str, Any],
    crosswalk: dict[str, Any],
    legacy: dict[str, Any],
) -> dict[str, Any]:
    if rubric.get("schema_version") != "2.0":
        raise RubricError("unexpected v2 schema version")
    if rubric.get("canonical") is not False:
        raise RubricError("candidate rubric must not claim canonical authority")
    if rubric.get("status") != "proposed_unscored" or rubric.get("official_v2_score_available") is not False:
        raise RubricError("v2 must remain explicitly unscored")
    if rubric.get("point_total") != 100:
        raise RubricError("v2 total point budget must be exactly 100")
    if "earned" in rubric or "baseline_points" in rubric:
        raise RubricError("unscored rubric must not declare earned points")
    if rubric.get("target_release") != "v1.0":
        raise RubricError("v2 rubric cannot change the target product release")
    historical = rubric.get("legacy_baseline")
    if not isinstance(historical, dict) or (
        historical.get("earned_points"), historical.get("possible_points"),
        historical.get("commit"), historical.get("date"), historical.get("path")
    ) != (69, 100, BASELINE_SHA, "2026-10-20", str(LEGACY)):
        raise RubricError("historical 69/100 baseline was modified")
    if legacy.get("scoring", {}).get("baseline_commit") != BASELINE_SHA or legacy.get("scoring", {}).get("baseline_points") != 69:
        raise RubricError("legacy canonical baseline is no longer 69/100")
    if sum(x.get("earned", 0) for x in legacy.get("stages", [])) != 69:
        raise RubricError("legacy stage earned points no longer total 69")
    policy = rubric.get("policy")
    if not isinstance(policy, dict) or not all(policy.get(key) is True for key in (
        "no_automatic_legacy_credit",
        "independent_release_gates",
        "independent_evidence_assessment_required",
        "customer_material_publication_prohibited",
        "no_score_for_unverified_live_or_field_claim",
        "no_infrastructure_padding",
    )):
        raise RubricError("candidate score and release/IP protections are required")
    if policy.get("qualification_tiers") != list(EVIDENCE_TIERS):
        raise RubricError("invalid qualification tier ladder")
    blockers = policy.get("hard_release_blockers")
    if not isinstance(blockers, list) or len(blockers) < 6 or any(not isinstance(x, str) or not x for x in blockers):
        raise RubricError("hard safety/security release blockers must be explicit")
    if "probabilistic" not in policy.get("domain_qualification", {}).get("reservoir", "").lower():
        raise RubricError("reservoir probabilistic uncertainty cannot be omitted")

    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != len(WEIGHTS):
        raise RubricError("seven distinct dimensions are required")
    seen_gates: set[str] = set()
    seen_dims: set[str] = set()
    total = 0
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            raise RubricError("dimension must be a mapping")
        dim_id = dimension.get("id")
        if dim_id in seen_dims or dim_id not in WEIGHTS:
            raise RubricError("duplicate/unknown dimension")
        seen_dims.add(dim_id)
        points = dimension.get("points")
        if isinstance(points, bool) or not isinstance(points, int) or points != WEIGHTS[dim_id]:
            raise RubricError(f"incorrect weight for dimension {dim_id}")
        if not isinstance(dimension.get("name"), str) or not dimension["name"]:
            raise RubricError("dimension name must be meaningful")
        if "earned" in dimension or "status" in dimension:
            raise RubricError("candidate dimensions cannot claim assessment")
        gates = dimension.get("gates")
        if not isinstance(gates, list) or not gates:
            raise RubricError("all dimensions need verifiable gates")
        subtotal = 0
        for gate in gates:
            if not isinstance(gate, dict):
                raise RubricError("gate must be a mapping")
            gate_id = gate.get("id")
            if not isinstance(gate_id, str) or not gate_id or gate_id in seen_gates:
                raise RubricError("duplicate/empty gate ID")
            seen_gates.add(gate_id)
            p = gate.get("points")
            if isinstance(p, bool) or not isinstance(p, int) or p <= 0:
                raise RubricError(f"invalid points for {gate_id}")
            if gate.get("minimum_evidence_tier") not in EVIDENCE_TIERS:
                raise RubricError(f"invalid evidence tier for {gate_id}")
            if not isinstance(gate.get("acceptance"), str) or len(gate["acceptance"]) < 40:
                raise RubricError(f"missing substantive acceptance for {gate_id}")
            if not isinstance(gate.get("title"), str) or not gate["title"]:
                raise RubricError(f"missing gate title for {gate_id}")
            if any(key in gate for key in ("earned", "status", "qualified", "evidence")):
                raise RubricError(f"unscored v2 gate {gate_id} must not claim earned credit")
            subtotal += p
        if subtotal != points:
            raise RubricError(f"gate points do not sum to dimension {dim_id}")
        total += points
    if total != 100 or seen_dims != set(WEIGHTS):
        raise RubricError("v2 dimensions must total 100 with fixed approved weights")

    old: dict[str, dict[str, Any]] = {}
    for stage in legacy.get("stages", []):
        for gate in stage.get("gates", []):
            old[gate["id"]] = gate
    if len(old) != 34:
        raise RubricError("expected 34 legacy evidence gates")
    if crosswalk.get("schema_version") != "2.0" or crosswalk.get("legacy_path") != str(LEGACY) or crosswalk.get("candidate_rubric_path") != str(RUBRIC):
        raise RubricError("crosswalk paths/schema invalid")
    if crosswalk.get("legacy_baseline_commit") != BASELINE_SHA or (
        crosswalk.get("legacy_baseline_earned"), crosswalk.get("legacy_baseline_possible")
    ) != (69, 100):
        raise RubricError("crosswalk historical baseline modified")
    if crosswalk.get("credit_transfer") != "forbidden" or crosswalk.get("comparison_delta_policy") != "not_comparable_without_normalization":
        raise RubricError("forbid automatic credit and false score deltas")
    mapping = crosswalk.get("mapping")
    if not isinstance(mapping, list) or len(mapping) != len(old):
        raise RubricError("crosswalk must account for all 34 legacy gates")
    mapped_old: set[str] = set()
    covered_new: set[str] = set()
    for row in mapping:
        if not isinstance(row, dict):
            raise RubricError("crosswalk row must be a mapping")
        old_id = row.get("old_gate")
        if old_id not in old or old_id in mapped_old:
            raise RubricError("missing/duplicate/unknown legacy gate")
        mapped_old.add(old_id)
        source = old[old_id]
        if (row.get("old_title"), row.get("old_points"), row.get("old_earned")) != (
            source["title"], source["points"], source["earned"]
        ):
            raise RubricError(f"legacy evidence changed in crosswalk {old_id}")
        if row.get("disposition") != "reassess_no_automatic_credit":
            raise RubricError("legacy points may not be assigned without requalification")
        targets = row.get("candidate_gates")
        if not isinstance(targets, list) or not targets or len(targets) != len(set(targets)):
            raise RubricError(f"crosswalk targets required and unique for {old_id}")
        if set(targets) - seen_gates:
            raise RubricError(f"crosswalk has unknown target for {old_id}")
        covered_new.update(targets)
    if mapped_old != set(old):
        raise RubricError("crosswalk omits legacy gates")
    if set(crosswalk.get("net_new_candidate_gates", [])) != seen_gates - covered_new:
        raise RubricError("net-new v2 gate disclosure does not match the crosswalk")
    return {
        "candidate": "v2.0.0-rc.1",
        "status": "proposed_unscored",
        "canonical_v1": {"earned": 69, "possible": 100, "commit": BASELINE_SHA},
        "dimension_weights": {d["id"]: d["points"] for d in dimensions},
        "dimension_count": len(dimensions),
        "candidate_gates": len(seen_gates),
        "legacy_gates_mapped": len(mapped_old),
        "net_new_gates": sorted(seen_gates - covered_new),
        "v2_score": None,
        "release_qualification": "unchanged",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the proposed unscored CEPIO v2 rubric/crosswalk")
    parser.add_argument("--rubric", type=Path, default=RUBRIC)
    parser.add_argument("--crosswalk", type=Path, default=CROSSWALK)
    parser.add_argument("--legacy", type=Path, default=LEGACY)
    parser.add_argument("--check", action="store_true", help="validate only")
    parser.add_argument("--json", action="store_true", help="emit non-scoring structure metadata")
    args = parser.parse_args()
    result = validate(_read(args.rubric), _read(args.crosswalk), _read(args.legacy))
    if args.check:
        print("v2 candidate rubric/crosswalk valid; v2 score NOT ASSESSED")
    elif args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("CEPIO v2 candidate: unscored / non-canonical. Historical canonical v1: 69/100.")
        print(f"{result['dimension_count']} dimensions / {result['candidate_gates']} gates; no automatic credit transfer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
