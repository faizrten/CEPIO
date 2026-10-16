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
    assert report["semantic_check_pass_rate"] == pytest.approx(64 / 74)
    assert report["gap_triage_hash"] is not None
    assert report["gap_disposition_counts"] == {
        "CORE": 0,
        "DOMAIN": 0,
        "PROFILE": 0,
        "MAPPING": 0,
        "REJECT": 8,
    }


def test_persona_expansion_triage_now_contains_only_deliberate_rejections():
    triage = load_gap_triage(GAPS)

    assert triage.status == "accepted"
    assert triage.competency_pack_id == "drilling-contractor-persona-expansion-v0.2"

    by_id = {decision.id: decision for decision in triage.decisions}
    assert len(by_id) == 8
    assert all(decision.disposition == "REJECT" for decision in triage.decisions)

    # Exact-path challenges remain intentionally absent because CEPIO now has better
    # reusable composition patterns or because the capability is derived at runtime.
    assert "GAP-PE-002-DIRECT-ACTIVITY-ASSIGNMENT" in by_id
    assert "GAP-PE-005-DIRECT-WORK-RESPONSIBILITY" in by_id
    assert "GAP-PE-007-SERVICE-DELIVERY-BOUNDARY" in by_id
    assert "GAP-PE-008-OBSERVATION-ACTIVITY-EDGE" in by_id
    assert "GAP-PE-009-SERVICE-EVIDENCE" in by_id
    assert "GAP-PE-010-PROGRAM-DEVIATION" in by_id
    assert "GAP-PE-012-MOBILIZATION-CONSTRAINT" in by_id
    assert "GAP-PE-013-SUPPORT-EDGE" in by_id

    # Accepted common and domain additions are no longer active gaps.
    for resolved in {
        "GAP-PE-001-AUTHORITY",
        "GAP-PE-003-SHIFT-HANDOVER",
        "GAP-PE-006-ENERGY-ISOLATION",
        "GAP-PE-008-DRILLING-FLUID-OBSERVATION",
        "GAP-PE-009-CEMENTING",
        "GAP-PE-010-AUTHORITY",
        "GAP-PE-012-CREW-ROTATION",
        "GAP-PE-013-MARINE-SUPPORT-ASSET",
        "GAP-PE-014-PURCHASE-ORDER",
    }:
        assert resolved not in by_id
