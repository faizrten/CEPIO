from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "generalization/gaps/refinery-process-manufacturing-v0.1.1.yaml"

EXPECTED_MISSING_CAPABILITIES = {
    "production-constraint",
    "economic-exposure",
    "operating-envelope",
    "process-deviation",
    "barrier-model",
    "barrier-restoration",
    "management-of-change",
    "moc-authority",
    "lot-specification",
    "quality-disposition",
    "emissions-evidence",
    "energy-intensity",
    "production-loss",
    "constraint-dependencies",
    "restart-activity",
    "restart-work-controls",
    "restart-safety-and-approval",
}


def load_triage() -> dict:
    return yaml.safe_load(TRIAGE.read_text(encoding="utf-8"))


def test_triage_preserves_raw_and_normalized_baselines() -> None:
    triage = load_triage()
    assert triage["status"] == "proposed"
    assert triage["baseline"]["raw_v0_1"]["semantic_checks_percent"] == 46.3
    assert triage["baseline"]["raw_v0_1"]["question_status"] == {
        "PASS": 6,
        "PARTIAL": 5,
        "FAIL": 5,
        "ERROR": 0,
    }
    assert triage["baseline"]["normalized_v0_1_1"]["semantic_checks_percent"] == 58.5
    assert triage["baseline"]["normalized_v0_1_1"]["question_status"] == {
        "PASS": 6,
        "PARTIAL": 8,
        "FAIL": 2,
        "ERROR": 0,
    }


def test_every_normalized_missing_capability_has_architectural_coverage() -> None:
    triage = load_triage()
    covered: list[str] = []
    for decision in triage["decisions"]:
        covered.extend(decision["covers_capabilities"])

    counts = Counter(covered)
    assert set(counts) == EXPECTED_MISSING_CAPABILITIES
    assert all(count >= 1 for count in counts.values())
    # Restart release legitimately composes a common safety-barrier decision with
    # a process-domain startup/restart decision. No other capability is duplicated.
    assert {capability for capability, count in counts.items() if count > 1} == {
        "restart-safety-and-approval"
    }
    assert counts["restart-safety-and-approval"] == 2
    assert triage["baseline"]["normalized_v0_1_1"]["missing_capabilities"] == len(EXPECTED_MISSING_CAPABILITIES)


def test_dispositions_and_no_profile_shortcuts() -> None:
    triage = load_triage()
    dispositions = Counter(decision["disposition"] for decision in triage["decisions"])
    assert dispositions == Counter({"DOMAIN": 4, "CORE": 3, "REJECT": 3, "MAPPING": 1})
    assert dispositions["PROFILE"] == 0
    assert triage["summary"]["decisions"] == 11
    assert triage["summary"]["ontology_remediation_in_this_pr"] is False


def test_rejected_patterns_have_explicit_better_abstractions() -> None:
    triage = load_triage()
    rejected = [decision for decision in triage["decisions"] if decision["disposition"] == "REJECT"]
    assert {decision["id"] for decision in rejected} == {
        "GAP-RP-008-LOT-SPECIFICATION",
        "GAP-RP-008-QUALITY-DISPOSITION",
        "GAP-RP-009-EMISSION-LIMIT",
    }
    assert all(decision.get("replacement_layer") for decision in rejected)
    assert all(decision.get("proposed_resolution") for decision in rejected)
