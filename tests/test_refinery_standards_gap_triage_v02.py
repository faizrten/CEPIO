from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "generalization/gaps/refinery-process-manufacturing-v0.2.yaml"


def _triage():
    return yaml.safe_load(TRIAGE.read_text(encoding="utf-8"))


def test_refinery_v02_triage_preserves_measured_baseline():
    data = _triage()
    baseline = data["baseline"]
    assert baseline["semantic_checks_percent"] == 49.4
    assert baseline["question_status"] == {"PASS": 0, "PARTIAL": 12, "FAIL": 0, "ERROR": 0}
    assert baseline["questions"] == 12


def test_all_refinery_v02_questions_are_covered_by_triage():
    data = _triage()
    covered = {question_id for decision in data["decisions"] for question_id in decision["question_ids"]}
    expected = {f"RP-PE-{index:03d}" for index in range(1, 13)}
    assert expected <= covered


def test_refinery_v02_triage_distribution_is_intentional():
    data = _triage()
    decisions = data["decisions"]
    counts = {name: 0 for name in ["CORE", "DOMAIN", "PROFILE", "MAPPING", "REJECT"]}
    for decision in decisions:
        counts[decision["disposition"]] += 1

    assert len(decisions) == 18
    assert counts == {"CORE": 5, "DOMAIN": 7, "PROFILE": 0, "MAPPING": 3, "REJECT": 3}
    assert data["summary"]["dispositions"] == counts
    assert data["summary"]["ontology_remediation_in_this_pr"] is False


def test_external_device_and_noa_architecture_are_not_copied_into_canonical_domain():
    data = _triage()
    by_id = {decision["id"]: decision for decision in data["decisions"]}

    padim = by_id["GAP-RP2-007-PADIM-DEVICE-MODEL"]
    noa = by_id["GAP-RP2-012-NAMUR-NOA-CHANNEL"]
    assert padim["disposition"] == "MAPPING"
    assert noa["disposition"] == "MAPPING"
    assert padim["owner_layer"] == "mappings"
    assert noa["owner_layer"] == "integrations"


def test_rejected_literals_do_not_proliferate_ontology():
    data = _triage()
    by_id = {decision["id"]: decision for decision in data["decisions"]}

    assert by_id["GAP-RP2-001-YIELD-MODEL"]["disposition"] == "REJECT"
    assert by_id["GAP-RP2-003-PROCEDURE-WORK-CONTROL-EDGE"]["disposition"] == "REJECT"
    assert by_id["GAP-RP2-006-ARC-FLASH-STUDY"]["disposition"] == "REJECT"


def test_no_customer_profile_semantics_are_introduced_by_refinery_v02_triage():
    data = _triage()
    assert all(decision["disposition"] != "PROFILE" for decision in data["decisions"])
    text = TRIAGE.read_text(encoding="utf-8").lower()
    for forbidden in ["satorp", "aramco", "sabic", "amiral"]:
        assert forbidden not in text
