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
        "PASS": 4,
        "PARTIAL": 10,
        "FAIL": 0,
        "ERROR": 0,
    }
    assert report["semantic_check_pass_rate"] == pytest.approx(54 / 74)
    assert report["gap_triage_hash"] is not None
    assert report["gap_disposition_counts"] == {
        "CORE": 3,
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

    assert by_id["GAP-PE-006-ENERGY-ISOLATION"].disposition == "CORE"
    assert by_id["GAP-PE-008-DRILLING-FLUID-OBSERVATION"].disposition == "DOMAIN"
    assert by_id["GAP-PE-009-CEMENTING"].disposition == "DOMAIN"
    assert by_id["GAP-PE-014-PURCHASE-ORDER"].disposition == "CORE"

    # Authority and handover gaps have been remediated and therefore must no longer
    # appear in the active triage ledger.
    assert "GAP-PE-001-AUTHORITY" not in by_id
    assert "GAP-PE-003-SHIFT-HANDOVER" not in by_id
    assert "GAP-PE-010-AUTHORITY" not in by_id

    # Direct person-to-activity/work edges and drilling-only service semantics remain
    # rejected in favor of reusable assignment/service patterns.
    assert by_id["GAP-PE-002-DIRECT-ACTIVITY-ASSIGNMENT"].disposition == "REJECT"
    assert by_id["GAP-PE-005-DIRECT-WORK-RESPONSIBILITY"].disposition == "REJECT"
    assert by_id["GAP-PE-007-SERVICE-DELIVERY-BOUNDARY"].disposition == "REJECT"
    assert by_id["GAP-PE-012-MOBILIZATION-CONSTRAINT"].disposition == "REJECT"

    # The wider persona challenge still provides no evidence that customer-specific
    # semantics belong in the CEPIO canonical layers.
    assert all(decision.disposition != "PROFILE" for decision in triage.decisions)
