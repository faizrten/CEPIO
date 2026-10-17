from pathlib import Path

import yaml

from cepio.generalization import (
    load_archetype,
    load_pack,
    load_personas,
    load_standards,
    run_harness,
    stable_hash,
    validate_cross_references,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"
ARCHETYPE = BASE / "archetypes/drilling-contractor-v0.1.yaml"
LEGACY_PERSONAS = BASE / "personas/drilling-contractor-v0.2.yaml"
PERSONAS = BASE / "personas/drilling-contractor-persona-expansion-v0.3.yaml"
COMPETENCY = BASE / "competency/drilling-contractor-domain-qualification-v0.4.yaml"
STANDARDS = BASE / "standards/drilling-references.yaml"
GAPS = BASE / "gaps/drilling-contractor-domain-qualification-v0.4.yaml"


def test_v03_persona_expansion_is_additive_to_v02():
    legacy = load_personas(LEGACY_PERSONAS)
    expansion = load_personas(PERSONAS)
    expansion_source = yaml.safe_load(PERSONAS.read_text(encoding="utf-8"))
    legacy_ids = {persona.id for persona in legacy.personas}
    expansion_ids = {persona.id for persona in expansion.personas}

    assert expansion.id == "drilling-contractor-persona-expansion-v0.3"
    assert expansion_source["extends"] == legacy.id
    assert len(legacy_ids) == 24
    assert len(expansion_ids) == 7
    assert expansion_ids.isdisjoint(legacy_ids)
    assert expansion_ids == {
        "enterprise-operations-director",
        "fleet-performance-manager",
        "drilling-optimization-engineer",
        "contract-performance-manager",
        "digital-transformation-lead",
        "industrial-data-product-owner",
        "ai-operations-governance-lead",
    }
    assert len(legacy_ids | expansion_ids) == 31


def test_v04_pack_is_frozen_and_covers_every_added_persona_and_band():
    pack = load_pack(COMPETENCY)
    personas = load_personas(PERSONAS)
    referenced = {persona for question in pack.questions for persona in question.personas}

    assert pack.id == "drilling-contractor-domain-qualification-v0.4"
    assert pack.version == "0.4"
    assert pack.frozen is True
    assert len(pack.questions) == 9
    assert {question.scope for question in pack.questions} == {
        "enterprise",
        "operational-optimization",
        "agentic-operations",
    }
    assert {persona.id for persona in personas.personas} <= referenced

    validate_cross_references(
        pack,
        load_archetype(ARCHETYPE),
        personas,
        load_standards(STANDARDS),
    )


def test_v04_frozen_questions_cannot_be_silently_weakened():
    pack = load_pack(COMPETENCY)
    assert stable_hash(pack.model_dump(mode="json")) == (
        "4c16efb2c64d5cf9bf70d9987c3693b20147dd89e3e8a2c48b0f82c2153fe05a"
    )


def test_v04_benchmark_retains_semantic_pressure_and_accepted_gap_triage():
    report = run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS, STANDARDS, GAPS)

    assert report["evaluation_contract"] == "capability-alternatives"
    assert report["question_count"] == 9
    assert report["status_counts"] == {"PASS": 7, "PARTIAL": 1, "FAIL": 1, "ERROR": 0}
    assert report["semantic_check_pass_rate"] == 9 / 11
    assert report["gap_disposition_counts"] == {
        "CORE": 2,
        "DOMAIN": 0,
        "PROFILE": 0,
        "MAPPING": 0,
        "REJECT": 0,
    }
    assert sum(
        result["status"] in {"PARTIAL", "FAIL"} for result in report["results"]
    ) == 2
    assert all(
        result["gap_decisions"]
        for result in report["results"]
        if result["status"] in {"PARTIAL", "FAIL"}
    )
    assert all(
        result["runtime_status"] == "NOT_RUN"
        for result in report["results"]
        if result["id"] in {"DC-DQ-007", "DC-DQ-008", "DC-DQ-009"}
    )
