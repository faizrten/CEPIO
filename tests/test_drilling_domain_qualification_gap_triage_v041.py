from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GAPS = ROOT / "generalization/gaps/drilling-contractor-domain-qualification-v0.4.1.yaml"

EXPECTED = {
    "DC-DQ-009": "GAP-DQ-009-PREDICTION-INFERENCE",
    "DC-DQ-011": "GAP-DQ-011-RECOMMENDATION-EVIDENCE",
    "DC-DQ-014": "GAP-DQ-014-OPERATIONAL-PLAN-REVISION",
    "DC-DQ-015": "GAP-DQ-015-OUTCOME-VALUE-ATTRIBUTION",
}


def _data():
    return yaml.safe_load(GAPS.read_text())


def test_gap_triage_matches_normalized_v041_failures():
    data = _data()
    decisions = {item["question_id"]: item for item in data["decisions"]}
    assert set(decisions) == set(EXPECTED)
    assert {question: decisions[question]["id"] for question in decisions} == EXPECTED


def test_all_v041_gaps_are_reusable_core_semantics():
    data = _data()
    decisions = data["decisions"]
    assert len(decisions) == 4
    assert {item["disposition"] for item in decisions} == {"CORE"}
    assert {item["replacement_layer"] for item in decisions} == {"CORE"}
    assert not any(item["disposition"] in {"DOMAIN", "PROFILE", "MAPPING"} for item in decisions)


def test_remediation_is_owned_by_common_modules_not_drilling():
    data = _data()
    owners = {item["owner_module"] for item in data["decisions"]}
    assert owners == {"agentic_operations", "kinetic", "performance"}
