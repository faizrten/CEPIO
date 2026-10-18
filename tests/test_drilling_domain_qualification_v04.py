import hashlib
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
PERSONAS_V02 = BASE / "personas/drilling-contractor-v0.2.yaml"
PERSONAS_V03 = BASE / "personas/drilling-contractor-v0.3.yaml"
COMPETENCY = BASE / "competency/drilling-contractor-domain-qualification-v0.4.yaml"
NORMALIZER_V041 = ROOT / "scripts/build_drilling_domain_qualification_v041.py"
STANDARDS = BASE / "standards/drilling-references.yaml"

# Git-blob digests intentionally pin the complete frozen v0.4 payload and the
# complete deterministic v0.4.1 normalizer. Because v0.4.1 is derived only
# from these two pinned inputs, changing any question text, terms, edges,
# alternatives, or normalization rule requires a new benchmark version and a
# deliberate digest update.
FROZEN_V04_BLOB_SHA = "a72144154a06ef3b2010e1a4db08b754f779e329"
FROZEN_V041_NORMALIZER_BLOB_SHA = "2452cb46b81d98a82d79ac72edfe6dd1186286dc"

ADDED_PERSONAS = {
    "chief-executive",
    "chief-operating-officer",
    "chief-financial-officer",
    "vp-drilling-operations",
    "drilling-performance-engineer",
    "contract-manager",
    "digital-ai-leader",
}


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


def test_frozen_domain_qualification_contract_inputs_are_content_pinned():
    assert _git_blob_sha(COMPETENCY) == FROZEN_V04_BLOB_SHA
    assert _git_blob_sha(NORMALIZER_V041) == FROZEN_V041_NORMALIZER_BLOB_SHA


def test_v03_personas_are_additive_to_v02():
    prior = load_personas(PERSONAS_V02)
    current = load_personas(PERSONAS_V03)
    prior_ids = {persona.id for persona in prior.personas}
    current_ids = {persona.id for persona in current.personas}

    assert len(prior_ids) == 24
    assert len(current_ids) == 31
    assert prior_ids <= current_ids
    assert current_ids - prior_ids == ADDED_PERSONAS


def test_domain_qualification_pack_is_frozen_and_balanced_across_three_bands():
    pack = load_pack(COMPETENCY)
    assert pack.frozen is True
    assert len(pack.questions) == 15

    tags = [set(question.capability_tags) for question in pack.questions]
    assert sum("enterprise" in item for item in tags) == 5
    assert sum("optimization" in item for item in tags) == 5
    assert sum("agentic" in item for item in tags) == 5


def test_every_new_persona_is_exercised_by_domain_qualification():
    pack = load_pack(COMPETENCY)
    referenced = {persona for question in pack.questions for persona in question.personas}
    assert ADDED_PERSONAS <= referenced


def test_domain_qualification_cross_references_are_clean():
    pack = load_pack(COMPETENCY)
    archetype = load_archetype(ARCHETYPE)
    personas = load_personas(PERSONAS_V03)
    standards = load_standards(STANDARDS)
    validate_cross_references(pack, archetype, personas, standards)


def test_v04_creates_real_domain_qualification_pressure_before_remediation():
    report = run_harness(ROOT, ARCHETYPE, COMPETENCY, PERSONAS_V03, STANDARDS)
    assert report["question_count"] == 15
    assert sum(report["status_counts"].values()) == 15
    assert report["status_counts"]["ERROR"] == 0
    assert report["status_counts"]["PARTIAL"] + report["status_counts"]["FAIL"] > 0
    assert report["semantic_check_pass_rate"] < 1.0
