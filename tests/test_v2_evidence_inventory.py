"""Negative controls for the unscored v2 evidence triage."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

PATH = Path("scripts/v2_evidence_inventory.py")
SPEC = importlib.util.spec_from_file_location("v2_evidence_inventory", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def inputs():
    return (
        yaml.safe_load(MODULE.DEFAULT_INVENTORY.read_text(encoding="utf-8")),
        yaml.safe_load(MODULE.DEFAULT_RUBRIC.read_text(encoding="utf-8")),
    )


def test_complete_public_inventory_has_no_v2_score():
    inventory, rubric = inputs()
    result = MODULE.validate_inventory(inventory, rubric)
    assert result["candidate_gates"] == 23
    assert result["canonical_v2_score"] is None
    assert result["historical_v1_score"] == "69/100"


def test_inventory_cannot_claim_canonical_points():
    inventory, rubric = inputs()
    inventory["canonical_v2_score"] = 10
    with pytest.raises(MODULE.EvidenceInventoryError, match="canonical v2 score"):
        MODULE.validate_inventory(inventory, rubric)


def test_inventory_cannot_upgrade_unreviewed_gate():
    inventory, rubric = inputs()
    inventory["gates"][0]["scoring_status"] = "qualified"
    with pytest.raises(MODULE.EvidenceInventoryError, match="premature qualification"):
        MODULE.validate_inventory(inventory, rubric)


def test_no_private_case_refs_in_public_inventory():
    inventory, rubric = inputs()
    inventory["gates"][0]["candidate_public_refs"] = ["CEPIO-Labs/private-sealed-holdout"]
    with pytest.raises(MODULE.EvidenceInventoryError, match="non-public"):
        MODULE.validate_inventory(inventory, rubric)


def test_all_candidate_gates_must_be_audited():
    inventory, rubric = inputs()
    inventory["gates"] = inventory["gates"][:-1]
    with pytest.raises(MODULE.EvidenceInventoryError, match="exactly every"):
        MODULE.validate_inventory(inventory, rubric)


def test_duplicate_gate_is_rejected():
    inventory, rubric = inputs()
    inventory["gates"][1]["gate_id"] = inventory["gates"][0]["gate_id"]
    with pytest.raises(MODULE.EvidenceInventoryError, match="duplicate"):
        MODULE.validate_inventory(inventory, rubric)


def test_missing_gap_description_is_rejected():
    inventory, rubric = inputs()
    inventory["gates"][2]["next_qualification"] = ""
    with pytest.raises(MODULE.EvidenceInventoryError, match="next_qualification"):
        MODULE.validate_inventory(inventory, rubric)


def test_unqualified_rubric_cannot_be_replaced_with_fake_canonical():
    inventory, rubric = inputs()
    rubric["canonical"] = True
    with pytest.raises(MODULE.EvidenceInventoryError, match="unscored candidate"):
        MODULE.validate_inventory(inventory, rubric)
