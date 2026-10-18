from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

DEFAULT_SCORECARD = Path("config/v1-scorecard.yaml")
ALLOWED_STATUSES = {"planned", "in_progress", "qualified"}


class ScorecardError(ValueError):
    pass


def load_scorecard(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ScorecardError("scorecard root must be a mapping")
    validate_scorecard(data)
    return data


def _number(value: Any, *, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ScorecardError(f"{field} must be numeric")
    return float(value)


def validate_scorecard(data: dict[str, Any]) -> None:
    scoring = data.get("scoring")
    stages = data.get("stages")
    if not isinstance(scoring, dict) or not isinstance(stages, list) or not stages:
        raise ScorecardError("scorecard requires scoring metadata and at least one stage")

    total_points = _number(scoring.get("total_points"), field="scoring.total_points")
    baseline_points = _number(scoring.get("baseline_points"), field="scoring.baseline_points")

    stage_points_total = 0.0
    stage_earned_total = 0.0
    gate_ids: set[str] = set()

    for stage in stages:
        if not isinstance(stage, dict):
            raise ScorecardError("each stage must be a mapping")
        stage_id = str(stage.get("id", "")).strip()
        if not stage_id:
            raise ScorecardError("stage id must be non-empty")
        points = _number(stage.get("points"), field=f"stage {stage_id}.points")
        earned = _number(stage.get("earned"), field=f"stage {stage_id}.earned")
        gates = stage.get("gates")
        if not isinstance(gates, list) or not gates:
            raise ScorecardError(f"stage {stage_id} must contain gates")

        gate_points = 0.0
        gate_earned = 0.0
        for gate in gates:
            if not isinstance(gate, dict):
                raise ScorecardError(f"stage {stage_id} contains a non-mapping gate")
            gate_id = str(gate.get("id", "")).strip()
            if not gate_id:
                raise ScorecardError(f"stage {stage_id} has a gate without an id")
            if gate_id in gate_ids:
                raise ScorecardError(f"duplicate gate id: {gate_id}")
            gate_ids.add(gate_id)

            gate_points_value = _number(gate.get("points"), field=f"gate {gate_id}.points")
            gate_earned_value = _number(gate.get("earned"), field=f"gate {gate_id}.earned")
            if gate_points_value <= 0:
                raise ScorecardError(f"gate {gate_id} points must be > 0")
            if gate_earned_value < 0 or gate_earned_value > gate_points_value:
                raise ScorecardError(f"gate {gate_id} earned points must be between 0 and {gate_points_value:g}")

            status = gate.get("status")
            if status not in ALLOWED_STATUSES:
                raise ScorecardError(f"gate {gate_id} has invalid status {status!r}")
            if status == "qualified" and gate_earned_value != gate_points_value:
                raise ScorecardError(f"qualified gate {gate_id} must earn all of its points")
            if status == "planned" and gate_earned_value != 0:
                raise ScorecardError(f"planned gate {gate_id} cannot have earned points")

            evidence = gate.get("evidence")
            if not isinstance(evidence, list):
                raise ScorecardError(f"gate {gate_id} evidence must be a list")
            if gate_earned_value > 0 and not any(str(item).strip() for item in evidence):
                raise ScorecardError(f"gate {gate_id} has earned points without evidence")

            gate_points += gate_points_value
            gate_earned += gate_earned_value

        if abs(gate_points - points) > 1e-9:
            raise ScorecardError(
                f"stage {stage_id} gate points ({gate_points:g}) do not equal stage points ({points:g})"
            )
        if abs(gate_earned - earned) > 1e-9:
            raise ScorecardError(
                f"stage {stage_id} gate earned ({gate_earned:g}) do not equal stage earned ({earned:g})"
            )
        if earned > points:
            raise ScorecardError(f"stage {stage_id} earned points exceed stage points")

        stage_points_total += points
        stage_earned_total += earned

    if abs(stage_points_total - total_points) > 1e-9:
        raise ScorecardError(
            f"stage points ({stage_points_total:g}) do not equal scoring.total_points ({total_points:g})"
        )
    if abs(stage_earned_total - baseline_points) > 1e-9:
        raise ScorecardError(
            f"earned points ({stage_earned_total:g}) do not equal scoring.baseline_points ({baseline_points:g})"
        )


def calculate(data: dict[str, Any]) -> dict[str, Any]:
    total = float(data["scoring"]["total_points"])
    earned = sum(float(stage["earned"]) for stage in data["stages"])
    stages = []
    for stage in data["stages"]:
        points = float(stage["points"])
        stage_earned = float(stage["earned"])
        stages.append(
            {
                "id": stage["id"],
                "name": stage["name"],
                "release_scope": stage["release_scope"],
                "earned": stage_earned,
                "points": points,
                "completion_pct": round((stage_earned / points) * 100, 1),
            }
        )
    return {
        "product": data["product"],
        "target_release": data["target_release"],
        "baseline_date": data["scoring"]["baseline_date"],
        "earned": earned,
        "points": total,
        "completion_pct": round((earned / total) * 100, 1),
        "stages": stages,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['product']} {result['target_release']} completion",
        "",
        f"**{result['completion_pct']:.1f}% complete ({result['earned']:g}/{result['points']:g} points)**",
        "",
        "| Stage | Release | Earned | Completion |",
        "| --- | --- | ---: | ---: |",
    ]
    for stage in result["stages"]:
        lines.append(
            f"| {stage['name']} | {stage['release_scope']} | "
            f"{stage['earned']:g}/{stage['points']:g} | {stage['completion_pct']:.1f}% |"
        )
    lines.extend(
        [
            "",
            "This score is a maturity indicator. Product releases remain governed by their explicit release gates.",
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
