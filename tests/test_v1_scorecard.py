from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.v1_scorecard import ScorecardError, calculate, load_scorecard, validate_scorecard


SCORECARD = Path("config/v1-scorecard.yaml")


def raw_scorecard() -> dict:
    return yaml.safe_load(SCORECARD.read_text(encoding="utf-8"))


def test_baseline_is_exactly_sixty_three_percent() -> None:
    result = calculate(load_scorecard(SCORECARD))

    assert result["earned"] == 63
    assert result["points"] == 100
    assert result["completion_pct"] == 63.0


def test_stage_and_gate_weights_are_self_consistent() -> None:
    data = load_scorecard(SCORECARD)

    assert sum(stage["points"] for stage in data["stages"]) == 100
    assert sum(stage["earned"] for stage in data["stages"]) == 63
    for stage in data["stages"]:
        assert sum(gate["points"] for gate in stage["gates"]) == stage["points"]
        assert sum(gate["earned"] for gate in stage["gates"]) == stage["earned"]


def test_earned_points_require_evidence() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    gate["evidence"] = []

    with pytest.raises(ScorecardError, match="earned points without evidence"):
        validate_scorecard(data)


def test_qualified_gate_must_earn_all_points() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    gate["earned"] = gate["points"] - 1
    data["stages"][0]["earned"] -= 1
    data["scoring"]["baseline_points"] -= 1

    with pytest.raises(ScorecardError, match="qualified gate"):
        validate_scorecard(data)


def test_stage_points_cannot_drift_from_gate_points() -> None:
    data = deepcopy(raw_scorecard())
    data["stages"][0]["points"] += 1
    data["scoring"]["total_points"] += 1

    with pytest.raises(ScorecardError, match="gate points"):
        validate_scorecard(data)


def test_total_weight_must_remain_one_hundred() -> None:
    data = deepcopy(raw_scorecard())
    data["scoring"]["total_points"] = 101

    with pytest.raises(ScorecardError, match="do not equal scoring.total_points"):
        validate_scorecard(data)
