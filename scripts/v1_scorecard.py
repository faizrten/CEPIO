from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

import yaml

DEFAULT_SCORECARD = Path("config/v1-scorecard.yaml")
ALLOWED_STATUSES = {"planned", "in_progress", "qualified"}
SCORING_EVIDENCE_STATES = {"merged", "qualified", "main"}
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ScorecardError(ValueError):
    """Raised when the canonical scorecard violates its governance contract."""


def load_scorecard(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ScorecardError("scorecard root must be a mapping")
    validate_scorecard(data)
    return data


def _integer(value: Any, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ScorecardError(f"{field} must be an integer")
    return value


def _non_empty(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScorecardError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_rules(scoring: dict[str, Any]) -> None:
    rules = scoring.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ScorecardError("scoring.rules must be a non-empty list")
    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ScorecardError("each scoring rule must be a mapping")
        rule_id = _non_empty(rule.get("id"), field="scoring rule id")
        _non_empty(rule.get("text"), field=f"scoring rule {rule_id}.text")
        if rule_id in seen:
            raise ScorecardError(f"duplicate scoring rule id: {rule_id}")
        seen.add(rule_id)


def _validate_evidence(gate_id: str, evidence: Any) -> int:
    if not isinstance(evidence, list):
        raise ScorecardError(f"gate {gate_id} evidence must be a list")

    scoring_count = 0
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ScorecardError(f"gate {gate_id} evidence[{index}] must be a mapping")
        _non_empty(item.get("kind"), field=f"gate {gate_id} evidence[{index}].kind")
        _non_empty(item.get("ref"), field=f"gate {gate_id} evidence[{index}].ref")
        state = _non_empty(item.get("state"), field=f"gate {gate_id} evidence[{index}].state")
        _non_empty(item.get("claim"), field=f"gate {gate_id} evidence[{index}].claim")
        counts = item.get("counts_toward_score")
        if not isinstance(counts, bool):
            raise ScorecardError(
                f"gate {gate_id} evidence[{index}].counts_toward_score must be boolean"
            )
        if counts and state not in SCORING_EVIDENCE_STATES:
            raise ScorecardError(
                f"gate {gate_id} evidence {item['ref']!r} cannot count while state={state!r}"
            )
        if counts:
            scoring_count += 1
    return scoring_count


def validate_scorecard(data: dict[str, Any]) -> None:
    if data.get("canonical") is not True:
        raise ScorecardError("canonical scorecard must set canonical: true")
    _non_empty(data.get("schema_version"), field="schema_version")
    _non_empty(data.get("scorecard_version"), field="scorecard_version")
    _non_empty(data.get("product"), field="product")
    _non_empty(data.get("target_release"), field="target_release")
    _non_empty(data.get("north_star"), field="north_star")

    scoring = data.get("scoring")
    stages = data.get("stages")
    if not isinstance(scoring, dict) or not isinstance(stages, list) or not stages:
        raise ScorecardError("scorecard requires scoring metadata and at least one stage")

    total_points = _integer(scoring.get("total_points"), field="scoring.total_points")
    baseline_points = _integer(scoring.get("baseline_points"), field="scoring.baseline_points")
    if total_points != 100:
        raise ScorecardError("scoring.total_points must equal exactly 100")
    if baseline_points < 0 or baseline_points > total_points:
        raise ScorecardError("scoring.baseline_points must be between 0 and 100")
    baseline_commit = _non_empty(scoring.get("baseline_commit"), field="scoring.baseline_commit")
    if not COMMIT_RE.fullmatch(baseline_commit):
        raise ScorecardError("scoring.baseline_commit must be a 40-character lowercase git SHA")
    _non_empty(scoring.get("baseline_date"), field="scoring.baseline_date")
    _non_empty(scoring.get("governance_document"), field="scoring.governance_document")
    _validate_rules(scoring)

    stage_points_total = 0
    stage_earned_total = 0
    stage_ids: set[str] = set()
    gate_ids: set[str] = set()

    for stage in stages:
        if not isinstance(stage, dict):
            raise ScorecardError("each stage must be a mapping")
        stage_id = _non_empty(stage.get("id"), field="stage id")
        if stage_id in stage_ids:
            raise ScorecardError(f"duplicate stage id: {stage_id}")
        stage_ids.add(stage_id)
        _non_empty(stage.get("name"), field=f"stage {stage_id}.name")
        _non_empty(stage.get("release_scope"), field=f"stage {stage_id}.release_scope")
        points = _integer(stage.get("points"), field=f"stage {stage_id}.points")
        earned = _integer(stage.get("earned"), field=f"stage {stage_id}.earned")
        gates = stage.get("gates")
        if points <= 0:
            raise ScorecardError(f"stage {stage_id} points must be > 0")
        if earned < 0 or earned > points:
            raise ScorecardError(f"stage {stage_id} earned points must be between 0 and {points}")
        if not isinstance(gates, list) or not gates:
            raise ScorecardError(f"stage {stage_id} must contain gates")

        gate_points = 0
        gate_earned = 0
        for gate in gates:
            if not isinstance(gate, dict):
                raise ScorecardError(f"stage {stage_id} contains a non-mapping gate")
            gate_id = _non_empty(gate.get("id"), field=f"stage {stage_id} gate id")
            if gate_id in gate_ids:
                raise ScorecardError(f"duplicate gate id: {gate_id}")
            gate_ids.add(gate_id)
            _non_empty(gate.get("title"), field=f"gate {gate_id}.title")

            gate_points_value = _integer(gate.get("points"), field=f"gate {gate_id}.points")
            gate_earned_value = _integer(gate.get("earned"), field=f"gate {gate_id}.earned")
            if gate_points_value <= 0:
                raise ScorecardError(f"gate {gate_id} points must be > 0")
            if gate_earned_value < 0 or gate_earned_value > gate_points_value:
                raise ScorecardError(
                    f"gate {gate_id} earned points must be between 0 and {gate_points_value}"
                )

            status = gate.get("status")
            if status not in ALLOWED_STATUSES:
                raise ScorecardError(f"gate {gate_id} has invalid status {status!r}")
            if status == "qualified" and gate_earned_value != gate_points_value:
                raise ScorecardError(f"qualified gate {gate_id} must earn all of its points")
            if gate_earned_value == gate_points_value and status != "qualified":
                raise ScorecardError(f"fully earned gate {gate_id} must be qualified")
            if status == "planned" and gate_earned_value != 0:
                raise ScorecardError(f"planned gate {gate_id} cannot have earned points")

            if 0 < gate_earned_value < gate_points_value:
                _non_empty(gate.get("credit_basis"), field=f"gate {gate_id}.credit_basis")

            scoring_evidence = _validate_evidence(gate_id, gate.get("evidence"))
            if gate_earned_value > 0 and scoring_evidence == 0:
                raise ScorecardError(f"gate {gate_id} has earned points without scoring evidence")

            gate_points += gate_points_value
            gate_earned += gate_earned_value

        if gate_points != points:
            raise ScorecardError(
                f"stage {stage_id} gate points ({gate_points}) do not equal stage points ({points})"
            )
        if gate_earned != earned:
            raise ScorecardError(
                f"stage {stage_id} gate earned ({gate_earned}) do not equal stage earned ({earned})"
            )
        stage_points_total += points
        stage_earned_total += earned

    if stage_points_total != 100:
        raise ScorecardError(f"stage points ({stage_points_total}) do not equal exactly 100")
    if stage_earned_total != baseline_points:
        raise ScorecardError(
            f"earned points ({stage_earned_total}) do not equal scoring.baseline_points "
            f"({baseline_points})"
        )


def calculate(data: dict[str, Any]) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    for stage in data["stages"]:
        stage_result = {
            "id": stage["id"],
            "name": stage["name"],
            "release_scope": stage["release_scope"],
            "earned": stage["earned"],
            "points": stage["points"],
            "completion_pct": round((stage["earned"] / stage["points"]) * 100, 1),
        }
        stages.append(stage_result)
        for gate in stage["gates"]:
            gates.append(
                {
                    "id": gate["id"],
                    "stage_id": stage["id"],
                    "title": gate["title"],
                    "status": gate["status"],
                    "earned": gate["earned"],
                    "points": gate["points"],
                    "remaining": gate["points"] - gate["earned"],
                }
            )

    total = data["scoring"]["total_points"]
    earned = sum(stage["earned"] for stage in data["stages"])
    remaining = sorted(
        (gate for gate in gates if gate["remaining"] > 0),
        key=lambda gate: (-gate["remaining"], gate["stage_id"], gate["id"]),
    )
    return {
        "product": data["product"],
        "target_release": data["target_release"],
        "scorecard_version": data["scorecard_version"],
        "baseline_date": data["scoring"]["baseline_date"],
        "baseline_commit": data["scoring"]["baseline_commit"],
        "earned": earned,
        "points": total,
        "completion_pct": round((earned / total) * 100, 1),
        "stages": stages,
        "gates": gates,
        "highest_remaining_gates": remaining[:5],
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['product']} {result['target_release']} completion",
        "",
        f"**{result['completion_pct']:.1f}% complete "
        f"({result['earned']}/{result['points']} points)**",
        "",
        f"Evidence snapshot: `{result['baseline_commit']}` ({result['baseline_date']})",
        "",
        "| Stage | Release | Earned | Completion |",
        "| --- | --- | ---: | ---: |",
    ]
    for stage in result["stages"]:
        lines.append(
            f"| {stage['name']} | {stage['release_scope']} | "
            f"{stage['earned']}/{stage['points']} | {stage['completion_pct']:.1f}% |"
        )
    lines.extend(["", "## Largest remaining gates", ""])
    for gate in result["highest_remaining_gates"]:
        lines.append(
            f"- {gate['id']} — {gate['title']}: "
            f"{gate['earned']}/{gate['points']} ({gate['remaining']} remaining)"
        )
    lines.extend(
        [
            "",
            "This score is a maturity indicator. Product releases remain governed by their "
            "explicit release gates.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and calculate the CEPIO v1.0 scorecard")
    parser.add_argument("--scorecard", type=Path, default=DEFAULT_SCORECARD)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    parser.add_argument("--check", action="store_true", help="validate only")
    args = parser.parse_args()

    data = load_scorecard(args.scorecard)
    if args.check:
        print("scorecard valid")
        return 0

    result = calculate(data)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
