from pathlib import Path

from cepio.generalization import (
    OntologyIndex,
    TermRequirement,
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


def _result(question_id: str):
    return next(item for item in _report()["results"] if item["id"] == question_id)


def test_drilling_specs_cross_reference_cleanly():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    personas = load_personas(PERSONAS)
    standards = load_standards(STANDARDS)
    validate_cross_references(pack, archetype, personas, standards)
    assert pack.frozen is True
    assert len(pack.questions) == 16


def test_gap_triage_exactly_covers_remaining_semantic_gaps():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    standards = load_standards(STANDARDS)
    triage = load_gap_triage(GAPS)
    report_without_triage = run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS, STANDARDS)
    validate_gap_triage(pack, archetype, standards, triage, report_without_triage["results"])
    assert triage.status == "accepted"
    assert len(triage.decisions) == 5


def test_stable_hash_is_order_independent_for_mappings():
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})


def test_remediation_improves_same_frozen_harness_without_erasing_gaps():
    report = _report()
    assert report["question_count"] == 16
    assert report["status_counts"] == {"PASS": 11, "PARTIAL": 5, "FAIL": 0, "ERROR": 0}
    assert round(report["semantic_check_pass_rate"], 3) == 0.946
    assert report["gap_triage_hash"]
    assert report["gap_disposition_counts"] == {
        "CORE": 0,
        "DOMAIN": 0,
        "PROFILE": 0,
        "MAPPING": 1,
        "REJECT": 4,
    }


def test_rig_well_campaign_semantics_are_present():
    assert _result("DC-CQ-001")["status"] == "PASS"


def test_npt_event_remains_rejected_in_favor_of_activity_classification():
    result = _result("DC-CQ-003")
    decision = result["gap_decisions"][0]
    assert result["status"] == "PARTIAL"
    assert decision["disposition"] == "REJECT"
    assert decision["replacement_layer"] == "DOMAIN"
    assert "NonProductiveTimeEvent" in decision["missing_semantics"][0]


def test_drilling_report_and_activity_are_resolved_but_external_codes_remain_mapping_gap():
    result = _result("DC-CQ-004")
    assert result["status"] == "PARTIAL"
    assert "https://cepio.org/ontology/drilling#DailyDrillingReport" not in result["missing"]
    assert "https://cepio.org/ontology/drilling#ActivityInterval" not in result["missing"]
    assert "https://cepio.org/ontology/drilling#ActivityCode" in result["missing"]
    assert result["gap_decisions"][0]["disposition"] == "MAPPING"


def test_competency_requirement_is_resolved_without_certificate_equals_competence():
    result = _result("DC-CQ-005")
    assert result["status"] == "PARTIAL"
    assert "https://cepio.org/ontology/workforce#CompetencyRequirement" not in result["missing"]
    assert len(result["missing"]) == 1
    assert result["gap_decisions"][0]["disposition"] == "REJECT"


def test_bop_assurance_now_passes():
    result = _result("DC-CQ-007")
    assert result["status"] == "PASS"
    assert result["missing"] == []
    assert result["gap_decisions"] == []


def test_dayrate_scalar_is_rejected_in_favor_of_common_commercial_rate_semantics():
    result = _result("DC-CQ-009")
    decision = result["gap_decisions"][0]
    ontology = OntologyIndex.from_repo(ROOT)
    assert result["status"] == "PARTIAL"
    assert decision["disposition"] == "REJECT"
    assert decision["replacement_layer"] == "CORE"
    assert decision["owner_module"] == "commercial"
    assert ontology.has_term(TermRequirement(iri="https://cepio.org/ontology/commercial#ContractRate", kind="class"))
    assert ontology.has_term(TermRequirement(iri="https://cepio.org/ontology/commercial#RateBasis", kind="class"))
    assert ontology.has_term(TermRequirement(iri="https://cepio.org/ontology/commercial#dayRate", kind="datatype_property"))
    assert not ontology.has_term(TermRequirement(iri="https://cepio.org/ontology/drilling#dayRate", kind="datatype_property"))


def test_campaign_readiness_constraint_is_not_promoted_without_cross_archetype_evidence():
    result = _result("DC-CQ-013")
    decision = result["gap_decisions"][0]
    assert result["status"] == "PARTIAL"
    assert decision["disposition"] == "REJECT"
    assert decision["benchmark_action"] == "retain-v0.1-gap"


def test_jackup_move_now_passes():
    result = _result("DC-CQ-014")
    assert result["status"] == "PASS"
    assert result["missing"] == []
    assert result["gap_decisions"] == []


def test_rejected_literal_semantics_remain_absent():
    ontology = OntologyIndex.from_repo(ROOT)
    rejected = [
        ("https://cepio.org/ontology/drilling#NonProductiveTimeEvent", "class"),
        ("https://cepio.org/ontology/drilling#ActivityCode", "class"),
        ("https://cepio.org/ontology/drilling#CampaignReadinessConstraint", "class"),
        ("https://cepio.org/ontology/workforce#meetsCompetencyRequirement", "object_property"),
    ]
    for iri, kind in rejected:
        assert not ontology.has_term(TermRequirement(iri=iri, kind=kind))


def test_runtime_evidence_checks_are_explicitly_not_run_in_v01():
    results = {item["id"]: item for item in _report()["results"]}
    assert results["DC-CQ-011"]["runtime_status"] == "NOT_RUN"
    assert results["DC-CQ-012"]["runtime_status"] == "NOT_RUN"
    assert _report()["runtime_evaluation"] == "not executed in v0.1"
