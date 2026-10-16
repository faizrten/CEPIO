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
ARCHETYPE = BASE / "archetypes/drilling-contractor-v0.1.yaml"
PERSONAS = BASE / "personas/drilling-contractor-v0.2.yaml"
COMPETENCY = BASE / "competency/drilling-contractor-persona-expansion-v0.2.yaml"
STANDARDS = BASE / "standards/drilling-references.yaml"

ADDED_PERSONAS = {
    "offshore-installation-manager",
    "driller",
    "assistant-driller",
    "subsea-well-control-engineer",
    "chief-mechanic",
    "chief-electrician",
    "directional-drilling-lead",
    "drilling-fluids-engineer",
    "cementing-supervisor",
    "operator-company-man",
    "finance-controller",
    "crewing-manager",
    "marine-rig-move-manager",
    "procurement-category-manager",
}


def test_v02_persona_pack_expands_scope_without_replacing_v01_roles():
    personas = load_personas(PERSONAS)
    ids = {persona.id for persona in personas.personas}
    assert len(ids) == 24
    assert ADDED_PERSONAS <= ids
    assert {
        "rig-manager", "drilling-superintendent", "toolpusher", "reliability-engineer",
        "maintenance-planner", "hse-manager", "competency-manager", "supply-chain-manager",
        "commercial-manager", "fleet-executive",
    } <= ids


def test_every_added_persona_is_exercised_by_a_frozen_competency_question():
    pack = load_pack(COMPETENCY)
    referenced = {persona for question in pack.questions for persona in question.personas}
    assert pack.frozen is True
    assert len(pack.questions) == 14
    assert ADDED_PERSONAS <= referenced


def test_expansion_pack_cross_references_standards_and_personas_cleanly():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    personas = load_personas(PERSONAS)
    standards = load_standards(STANDARDS)
    validate_cross_references(pack, archetype, personas, standards)


def test_expansion_pack_creates_real_semantic_pressure():
    report = run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS, STANDARDS)
    assert report["question_count"] == 14
    assert sum(report["status_counts"].values()) == 14
    assert report["status_counts"]["ERROR"] == 0
    assert report["status_counts"]["PARTIAL"] + report["status_counts"]["FAIL"] > 0
    assert report["semantic_check_pass_rate"] < 1.0
