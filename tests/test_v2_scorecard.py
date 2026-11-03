from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


MODULE_PATH = Path("scripts/v2_scorecard.py")
SPEC = importlib.util.spec_from_file_location("v2_scorecard", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
V2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V2)


def fixture():
    return tuple(
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (V2.RUBRIC, V2.CROSSWALK, V2.LEGACY)
    )


def test_candidate_is_unscored_and_history_is_intact():
    rubric, crosswalk, legacy = fixture()
    result = V2.validate(rubric, crosswalk, legacy)
    assert result["v2_score"] is None
    assert result["canonical_v1"]["earned"] == 69
    assert result["dimension_weights"] == V2.WEIGHTS
    assert result["dimension_count"] == 7
    assert result["legacy_gates_mapped"] == 34


def test_no_auto_transfer_or_new_canonical_claim():
    rubric, crosswalk, legacy = fixture()
    rubric["canonical"] = True
    with pytest.raises(V2.RubricError, match="canonical"):
        V2.validate(rubric, crosswalk, legacy)


def test_earned_points_in_candidate_are_rejected():
    rubric, crosswalk, legacy = fixture()
    rubric["dimensions"][0]["gates"][0]["earned"] = 3
    with pytest.raises(V2.RubricError, match="must not claim earned credit"):
        V2.validate(rubric, crosswalk, legacy)


def test_dimension_weight_change_is_rejected():
    rubric, crosswalk, legacy = fixture()
    rubric["dimensions"][0]["points"] = 11
    with pytest.raises(V2.RubricError, match="incorrect weight"):
        V2.validate(rubric, crosswalk, legacy)


def test_missing_legacy_crosswalk_gate_is_rejected():
    rubric, crosswalk, legacy = fixture()
    crosswalk["mapping"].pop()
    with pytest.raises(V2.RubricError, match="all 34 legacy gates"):
        V2.validate(rubric, crosswalk, legacy)


def test_historical_credit_misrepresentation_is_rejected():
    rubric, crosswalk, legacy = fixture()
    crosswalk["mapping"][0]["old_earned"] = 0
    with pytest.raises(V2.RubricError, match="legacy evidence changed"):
        V2.validate(rubric, crosswalk, legacy)


def test_unknown_new_gate_in_crosswalk_is_rejected():
    rubric, crosswalk, legacy = fixture()
    crosswalk["mapping"][0]["candidate_gates"] = ["NONEXISTENT"]
    with pytest.raises(V2.RubricError, match="unknown target"):
        V2.validate(rubric, crosswalk, legacy)


def test_proposed_score_cannot_skip_independent_tiers():
    rubric, crosswalk, legacy = fixture()
    rubric["dimensions"][2]["gates"][0]["minimum_evidence_tier"] = "merged_code_only"
    with pytest.raises(V2.RubricError, match="invalid evidence tier"):
        V2.validate(rubric, crosswalk, legacy)


def test_critical_domain_uncertainty_is_mandatory():
    rubric, crosswalk, legacy = fixture()
    rubric["policy"]["domain_qualification"]["reservoir"] = "Deterministic conclusion"
    with pytest.raises(V2.RubricError, match="reservoir probabilistic"):
        V2.validate(rubric, crosswalk, legacy)


def test_score_delta_is_not_fabricated():
    rubric, crosswalk, legacy = fixture()
    crosswalk["comparison_delta_policy"] = "subtract_score_directly"
    with pytest.raises(V2.RubricError, match="false score deltas"):
        V2.validate(rubric, crosswalk, legacy)
