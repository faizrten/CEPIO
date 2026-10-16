from pathlib import Path

import pytest

from cepio.generalization import (
    load_gap_triage,
    run_harness,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"
ARCHETYPE = BASE / "archetypes/drilling-contractor-v0.1.yaml"
PERSONAS = BASE / "personas/drilling-contractor-v0.2.yaml"
COMPETENCY = BASE / "competency/drilling-contractor-persona-expansion-v0.2.yaml"
STANDARDS = BASE / "standards/drilling-references.yaml"
GAPS = BASE / "gaps/drilling-contractor-persona-v0.2.yaml"


def test_persona_expansion_gap_triage_covers_every_current_gap():
    report = run_harness(
        ROOT,
        ARCHETYPE,
        COMPETENCY,
        PERSONAS,
        STANDARDS,
        GAPS,
    )

    assert report["question_count"] == 14
    assert report["status_counts"] == {
        "PASS": 6,
        "PARTIAL": 8,
        "FAIL": 0,
        "ERROR": 0,
    }
    assert report["semantic_check_pass_rate"] == pytest.approx(59 / 74)
    assert report["gap_triage_hash"] is not None
    assert report["gap_disposition_counts"] == {
        "CORE": 0,
        "DOMAIN": 3,
        "PROFILE": 0,
        "MAPPING": 0,
        "REJECT": 8,
    }


def test_persona_expansion_triage_preserves_architectural_boundaries():
    triage = load_gap_triage(GAPS)

    assert triage.status == "accepted"
    assert triage.competency_pack_id == "drilling-contractor-persona-expansion-v0.2"

    by_id = {decision.id: decision for decision in triage.decisions}

    assert by_id["GAP-PE-008-DRILLING-FLUID-OBSERVATION"].disposition == "DOMAIN"
    assert by_id["GAP-PE-009-CEMENTING"].disposition == "DOMAIN"
    assert by_id["GAP-PE-013-MARINE-SUPPORT-ASSET"].disposition == "DOMAIN"

    # Reusable authority, handover, isolation, rotation and purchase-order gaps have
    # been remediated and must no longer appear in active triage.
    for resolved in {
        "GAP-PE-001-AUTHORITY",
        "GAP-PE-003-SHIFT-HANDOVER",
        "GAP-PE-006-ENERGY-ISOLATION",
        "GAP-PE-010-AUTHORITY",
        "GAP-PE-012-CREW-ROTATION",
        "GAP-PE-014-PURCHASE-ORDER",
    }:
        assert resolved not in by_id

    # Direct person-to-activity/work edges and drilling-only service semantics remain
    # rejected in favor of reusable assignment/service patterns.
    assert by_id["GAP-PE-002-DIRECT-ACTIVITY-ASSIGNMENT"].disposition == "REJECT"
    assert by_id["GAP-PE-005-DIRECT-WORK-RESPONSIBILITY"].disposition == "REJECT"
    assert by_id["GAP-PE-007-SERVICE-DELIVERY-BOUNDARY"].disposition == "REJECT"
    assert by_id["GAP-PE-012-MOBILIZATION-CONSTRAINT"].disposition == "REJECT"

    # No customer-specific semantics have been required by the broader persona test.
    assert all(decision.disposition != "PROFILE" for decision in triage.decisions)
