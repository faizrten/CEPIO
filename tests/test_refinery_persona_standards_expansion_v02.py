from pathlib import Path

from cepio.generalization import (
    load_archetype,
    load_pack,
    load_personas,
    load_standards,
    run_harness,
    validate_cross_references,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"
ARCHETYPE = BASE / "archetypes/refinery-process-manufacturing-v0.1.yaml"
PERSONAS = BASE / "personas/refinery-process-manufacturing-v0.2.yaml"
COMPETENCY = BASE / "competency/refinery-process-manufacturing-persona-expansion-v0.2.yaml"
STANDARDS = BASE / "standards/refinery-process-references-v0.2.yaml"

ADDED_PERSONAS = {
    "refinery-economist",
    "production-scheduler",
    "field-operator",
    "process-control-engineer",
    "inspection-corrosion-engineer",
    "electrical-power-engineer",
    "instrumentation-analyzer-engineer",
    "engineering-information-manager",
    "asset-management-lead",
    "tank-farm-movements-manager",
    "production-assurance-engineer",
    "ot-automation-engineer",
}

EXPANDED_STANDARDS = {
    "isa-106-2023",
    "iec-62682-2022",
    "iso-20815-2026",
    "iso-55001-2024",
    "api-rp-580-4e",
    "api-rp-584-2e",
    "iso-15926-2-2003",
    "dexpi-2.0.1-2026",
    "cfihos-2.0-2025",
    "opc-30081-padim-1.02",
    "namur-noa-ne175-ne176",
    "ieee-841-2021",
    "ieee-1584-2018",
}


def test_v02_persona_pack_expands_refinery_scope_without_replacing_v01_roles():
    personas = load_personas(PERSONAS)
    ids = {persona.id for persona in personas.personas}
    assert len(ids) == 26
    assert ADDED_PERSONAS <= ids
    assert {
        "plant-manager",
        "operations-manager",
        "console-operator",
        "shift-supervisor",
        "process-engineer",
        "reliability-engineer",
        "maintenance-planner",
        "process-safety-manager",
        "quality-manager",
        "energy-manager",
        "environmental-manager",
        "turnaround-manager",
        "contractor-services-manager",
        "finance-controller",
    } <= ids


def test_every_added_refinery_persona_is_exercised_by_the_frozen_challenge():
    pack = load_pack(COMPETENCY)
    referenced = {persona for question in pack.questions for persona in question.personas}
    assert pack.frozen is True
    assert len(pack.questions) == 12
    assert ADDED_PERSONAS <= referenced


def test_v02_standards_registry_contains_the_expanded_reference_surface():
    standards = load_standards(STANDARDS)
    ids = {reference.id for reference in standards.references}
    assert EXPANDED_STANDARDS <= ids
    assert {"isa-95-2025", "iso-14224-2016", "iec-61511-series", "api-rp-754-4e", "iso-50001-2018"} <= ids


def test_expansion_pack_cross_references_archetype_personas_and_standards_cleanly():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    personas = load_personas(PERSONAS)
    standards = load_standards(STANDARDS)
    validate_cross_references(pack, archetype, personas, standards)


def test_expansion_pack_creates_real_new_semantic_pressure():
    report = run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS, STANDARDS)
    assert report["question_count"] == 12
    assert sum(report["status_counts"].values()) == 12
    assert report["status_counts"]["ERROR"] == 0
    assert report["status_counts"]["PARTIAL"] + report["status_counts"]["FAIL"] > 0
    assert report["semantic_check_pass_rate"] < 1.0


def test_expansion_is_source_neutral_and_contains_no_customer_profile_semantics():
    text = COMPETENCY.read_text(encoding="utf-8").lower()
    for forbidden in ["satorp", "aramco", "sabic", "amiral", "aro drilling"]:
        assert forbidden not in text
