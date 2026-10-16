from pathlib import Path

from cepio.generalization import (
    load_archetype,
    load_pack,
    load_personas,
    load_standards,
    validate_cross_references,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"


def test_refinery_pack_is_frozen_and_cross_references_are_valid() -> None:
    archetype = load_archetype(BASE / "archetypes/refinery-process-manufacturing-v0.1.yaml")
    pack = load_pack(BASE / "competency/refinery-process-manufacturing-v0.1.yaml")
    personas = load_personas(BASE / "personas/refinery-process-manufacturing-v0.1.yaml")
    standards = load_standards(BASE / "standards/refinery-process-references.yaml")

    validate_cross_references(pack, archetype, personas, standards)
    assert pack.frozen is True
    assert len(pack.questions) == 16
    assert len({question.id for question in pack.questions}) == 16


def test_refinery_pack_has_broad_operating_coverage() -> None:
    pack = load_pack(BASE / "competency/refinery-process-manufacturing-v0.1.yaml")
    tags = {tag for question in pack.questions for tag in question.capability_tags}

    required = {
        "process-unit",
        "operating-envelope",
        "reliability",
        "permit",
        "process-safety",
        "moc",
        "quality",
        "emissions",
        "energy",
        "turnaround",
        "service",
        "margin",
        "optimization",
        "restart",
    }
    assert required <= tags


def test_refinery_baseline_is_source_neutral() -> None:
    files = [
        BASE / "archetypes/refinery-process-manufacturing-v0.1.yaml",
        BASE / "personas/refinery-process-manufacturing-v0.1.yaml",
        BASE / "competency/refinery-process-manufacturing-v0.1.yaml",
    ]
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)

    for customer_name in ("aramco", "satorp", "sabic", "sipchem", "ma'aden", "maaden"):
        assert customer_name not in text


def test_every_question_has_semantic_capabilities() -> None:
    pack = load_pack(BASE / "competency/refinery-process-manufacturing-v0.1.yaml")
    assert all(question.capabilities for question in pack.questions)
    assert all(capability.alternatives for question in pack.questions for capability in question.capabilities)
