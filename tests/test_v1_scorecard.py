from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml


SCORECARD = Path("config/v1-scorecard.yaml")
SCRIPT = Path("scripts/v1_scorecard.py")
SPEC = importlib.util.spec_from_file_location("v1_scorecard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ScorecardError = MODULE.ScorecardError
calculate = MODULE.calculate
load_scorecard = MODULE.load_scorecard
render_markdown = MODULE.render_markdown
validate_scorecard = MODULE.validate_scorecard


def raw_scorecard() -> dict[str, Any]:
    payload = yaml.safe_load(SCORECARD.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_canonical_baseline_is_sixty_nine_percent() -> None:
    result = calculate(load_scorecard(SCORECARD))

    assert result["earned"] == 69
    assert result["points"] == 100
    assert result["completion_pct"] == 69.0
    assert result["baseline_commit"] == "a179e9cfc0dbf5e866a6a6aa143eb4290e79918d"


def test_stage_and_gate_weights_are_self_consistent() -> None:
    data = load_scorecard(SCORECARD)

    assert sum(stage["points"] for stage in data["stages"]) == 100
    assert sum(stage["earned"] for stage in data["stages"]) == 69
    for stage in data["stages"]:
        assert sum(gate["points"] for gate in stage["gates"]) == stage["points"]
        assert sum(gate["earned"] for gate in stage["gates"]) == stage["earned"]


def test_earned_points_require_scoring_evidence() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    gate["evidence"] = []

    with pytest.raises(ScorecardError, match="earned points without scoring evidence"):
        validate_scorecard(data)


def test_open_pull_request_cannot_count_toward_score() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    gate["evidence"][0]["state"] = "open"
    gate["evidence"][0]["counts_toward_score"] = True

    with pytest.raises(ScorecardError, match="cannot count while state='open'"):
        validate_scorecard(data)


def test_non_scoring_progress_evidence_cannot_support_earned_points() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    for evidence in gate["evidence"]:
        evidence["counts_toward_score"] = False

    with pytest.raises(ScorecardError, match="earned points without scoring evidence"):
        validate_scorecard(data)


def test_partial_credit_requires_explicit_credit_basis() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][1]["gates"][1]
    assert 0 < gate["earned"] < gate["points"]
    gate.pop("credit_basis")

    with pytest.raises(ScorecardError, match="credit_basis"):
        validate_scorecard(data)


def test_qualified_gate_must_earn_all_points() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    gate["earned"] = gate["points"] - 1
    gate["credit_basis"] = "test partial credit"
    data["stages"][0]["earned"] -= 1
    data["scoring"]["baseline_points"] -= 1

    with pytest.raises(ScorecardError, match="qualified gate"):
        validate_scorecard(data)


def test_fully_earned_gate_must_be_qualified() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][0]["gates"][0]
    gate["status"] = "in_progress"

    with pytest.raises(ScorecardError, match="fully earned gate"):
        validate_scorecard(data)


def test_planned_gate_cannot_have_earned_points() -> None:
    data = deepcopy(raw_scorecard())
    gate = data["stages"][1]["gates"][2]
    gate["earned"] = 1
    gate["credit_basis"] = "invalid planned credit"
    data["stages"][1]["earned"] += 1
    data["scoring"]["baseline_points"] += 1

    with pytest.raises(ScorecardError, match="planned gate"):
        validate_scorecard(data)


def test_stage_points_cannot_drift_from_gate_points() -> None:
    data = deepcopy(raw_scorecard())
    data["stages"][0]["points"] += 1

    with pytest.raises(ScorecardError, match="gate points"):
        validate_scorecard(data)


def test_total_weight_is_fixed_at_exactly_one_hundred() -> None:
    data = deepcopy(raw_scorecard())
    data["scoring"]["total_points"] = 101

    with pytest.raises(ScorecardError, match="must equal exactly 100"):
        validate_scorecard(data)


def test_baseline_commit_is_pinned_to_exact_git_sha() -> None:
    data = deepcopy(raw_scorecard())
    data["scoring"]["baseline_commit"] = "main"

    with pytest.raises(ScorecardError, match="40-character lowercase git SHA"):
        validate_scorecard(data)


def test_markdown_report_keeps_release_gate_disclaimer() -> None:
    result = calculate(load_scorecard(SCORECARD))
    report = render_markdown(result)

    assert "69.0% complete (69/100 points)" in report
    assert "Product releases remain governed by their explicit release gates" in report
    assert "Largest remaining gates" in report
