from pathlib import Path

from cepio.generalization import (
    load_archetype,
    load_gap_triage,
    load_pack,
    load_personas,
    load_standards,
    run_harness,
    stable_hash,
    validate_cross_references,
    validate_gap_triage,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"
ARCHETYPE = BASE / "archetypes/drilling-contractor-v0.1.yaml"
COMPETENCY = BASE / "competency/drilling-contractor-v0.1.yaml"
PERSONAS = BASE / "personas/drilling-contractor-v0.1.yaml"
STANDARDS = BASE / "standards/drilling-references.yaml"
GAPS = BASE / "gaps/drilling-contractor-v0.1.yaml"


def _report():
    return run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS, STANDARDS, GAPS)


def test_drilling_specs_cross_reference_cleanly():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    personas = load_personas(PERSONAS)
    standards = load_standards(STANDARDS)
    validate_cross_references(pack, archetype, personas, standards)
    assert pack.frozen is True
    assert len(pack.questions) == 16


def test_gap_triage_exactly_covers_current_semantic_gaps():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    standards = load_standards(STANDARDS)
    triage = load_gap_triage(GAPS)
    report_without_triage = run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS, STANDARDS)
    validate_gap_triage(pack, archetype, standards, triage, report_without_triage["results"])
    assert triage.status == "accepted"
    assert len(triage.decisions) == 9


def test_stable_hash_is_order_independent_for_mappings():
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})


def test_harness_surfaces_strengths_and_gaps():
    report = _report()
    assert report["question_count"] == 16
    assert report["status_counts"]["PASS"] > 0
    assert report["status_counts"]["PARTIAL"] + report["status_counts"]["FAIL"] > 0
    assert 0.0 < report["semantic_check_pass_rate"] < 1.0
    assert report["gap_triage_hash"]
    assert report["gap_disposition_counts"] == {
        "CORE": 1,
        "DOMAIN": 3,
        "PROFILE": 0,
        "MAPPING": 1,
        "REJECT": 4,
    }


def test_rig_well_campaign_semantics_are_present():
    result = next(item for item in _report()["results"] if item["id"] == "DC-CQ-001")
    assert result["status"] == "PASS"


def test_npt_event_is_rejected_in_favor_of_domain_activity_classification():
    result = next(item for item in _report()["results"] if item["id"] == "DC-CQ-003")
    decision = result["gap_decisions"][0]
    assert decision["disposition"] == "REJECT"
    assert decision["replacement_layer"] == "DOMAIN"
    assert "NonProductiveTimeEvent" in decision["missing_semantics"][0]


def test_bop_assurance_exposes_current_domain_gap():
    result = next(item for item in _report()["results"] if item["id"] == "DC-CQ-007")
    assert result["status"] != "PASS"
    assert "https://cepio.org/ontology/drilling#BlowoutPreventer" in result["missing"]
    assert result["gap_decisions"][0]["disposition"] == "DOMAIN"


def test_dayrate_scalar_is_rejected_in_favor_of_common_commercial_rate_semantics():
    result = next(item for item in _report()["results"] if item["id"] == "DC-CQ-009")
    decision = result["gap_decisions"][0]
    assert decision["disposition"] == "REJECT"
    assert decision["replacement_layer"] == "CORE"
    assert decision["owner_module"] == "commercial"


def test_campaign_readiness_constraint_is_not_promoted_without_cross_archetype_evidence():
    result = next(item for item in _report()["results"] if item["id"] == "DC-CQ-013")
    decision = result["gap_decisions"][0]
    assert decision["disposition"] == "REJECT"
    assert decision["benchmark_action"] == "retain-v0.1-gap"


def test_jackup_move_exposes_current_domain_gap():
    result = next(item for item in _report()["results"] if item["id"] == "DC-CQ-014")
    assert result["status"] != "PASS"
    assert "https://cepio.org/ontology/drilling#JackUpMove" in result["missing"]
    assert result["gap_decisions"][0]["disposition"] == "DOMAIN"


def test_runtime_evidence_checks_are_explicitly_not_run_in_v01():
    results = {item["id"]: item for item in _report()["results"]}
    assert results["DC-CQ-011"]["runtime_status"] == "NOT_RUN"
    assert results["DC-CQ-012"]["runtime_status"] == "NOT_RUN"
    assert _report()["runtime_evaluation"] == "not executed in v0.1"
