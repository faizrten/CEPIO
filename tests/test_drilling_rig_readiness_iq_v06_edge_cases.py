from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_rig_readiness_iq import (
    _assess_equipment,
    _assess_supply,
    _assess_well_control,
    _assess_workforce,
    _aware_datetime,
    _is_a,
    _normalized_status,
    _require_type,
)
from cepio.model import ObjectRef, OntologyObject, Relationship


AT = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


class _NoRegistryRuntime:
    type_registry = None


def _rel(
    runtime, rel_type: str, source_id: str, source_type: str, target_id: str, target_type: str
):
    runtime.add_relationship(
        Relationship(
            type=rel_type,
            source=ObjectRef(id=source_id, type=source_type),
            target=ObjectRef(id=target_id, type=target_type),
        )
    )


def test_readiness_helpers_fail_closed_on_type_status_and_time_shape():
    assert _is_a(_NoRegistryRuntime(), "Equipment", "Equipment") is True

    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="WO-1", type="WorkOrder", name="Wrong type"))
    with pytest.raises(ValueError, match="WO-1 is not a Equipment"):
        _require_type(runtime, "WO-1", "Equipment")

    with pytest.raises(ValueError, match="missing required normalized status"):
        _normalized_status(
            OntologyObject(id="EQ-NOSTATUS", type="Equipment", name="No-status equipment")
        )

    assert _aware_datetime(AT, label="at") == AT
    with pytest.raises(ValueError, match="must be an ISO-8601 timestamp"):
        _aware_datetime("not-a-date", label="at")
    with pytest.raises(ValueError, match="must be an ISO-8601 timestamp"):
        _aware_datetime(42, label="at")
    with pytest.raises(ValueError, match="must include timezone context"):
        _aware_datetime(datetime(2026, 10, 18, 12, 0), label="at")


def test_equipment_not_ready_branch_is_explicit():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="EQ-FAILED",
            type="DrillingEquipment",
            name="Failed top drive",
            properties={"status": "FAILED"},
        )
    )

    _, blockers = _assess_equipment(runtime, ["EQ-FAILED"])

    assert [item.code for item in blockers] == ["equipment.not-ready"]


def test_well_control_unscoped_test_is_a_blocker():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="WC-UNSCOPED",
            type="WellControlTest",
            name="Unscoped BOP test",
            properties={
                "status": "PASSED",
                "validTo": "2026-10-20T00:00:00+00:00",
            },
        )
    )

    _, blockers = _assess_well_control(runtime, ["WC-UNSCOPED"], assessment_time=AT)

    assert [item.code for item in blockers] == ["well-control.test-unscoped"]


def test_well_control_rejects_non_equipment_target(monkeypatch):
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="WC-BAD-TARGET",
            type="WellControlTest",
            name="BOP test",
            properties={
                "status": "PASSED",
                "validTo": "2026-10-20T00:00:00+00:00",
            },
        )
    )
    bad_target = OntologyObject(id="WO-NOT-EQUIPMENT", type="WorkOrder", name="Wrong target")
    original_neighbors = runtime.neighbors

    def neighbors(object_id: str, relationship_type: str | None = None):
        if object_id == "WC-BAD-TARGET" and relationship_type == "testsWellControlEquipment":
            return [bad_target]
        return original_neighbors(object_id, relationship_type)

    monkeypatch.setattr(runtime, "neighbors", neighbors)

    with pytest.raises(ValueError, match="target WO-NOT-EQUIPMENT is not Equipment"):
        _assess_well_control(runtime, ["WC-BAD-TARGET"], assessment_time=AT)


def test_workforce_at_risk_wrong_activity_and_unstaffed_are_explicit():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="ASG-AT-RISK",
            type="CrewAssignment",
            name="At-risk assignment",
            properties={"status": "AT_RISK"},
        )
    )

    _, blockers = _assess_workforce(
        runtime,
        ["ASG-AT-RISK"],
        planned_activity_id="ACT-PLANNED",
    )
    codes = {item.code for item in blockers}

    assert "workforce.assignment-at-risk" in codes
    assert "workforce.assignment-wrong-activity" in codes
    assert "workforce.assignment-unstaffed" in codes


def test_workforce_not_ready_and_missing_competency_requirement_are_explicit():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(id="ACT-1", type="ActivityInterval", name="Planned activity")
    )
    runtime.upsert_object(OntologyObject(id="PERSON-1", type="CrewMember", name="Crew member"))
    runtime.upsert_object(
        OntologyObject(
            id="ASG-BLOCKED",
            type="CrewAssignment",
            name="Blocked assignment",
            properties={"status": "BLOCKED"},
        )
    )
    _rel(
        runtime,
        "assignmentForActivity",
        "ASG-BLOCKED",
        "CrewAssignment",
        "ACT-1",
        "ActivityInterval",
    )
    _rel(runtime, "assignmentOf", "ASG-BLOCKED", "CrewAssignment", "PERSON-1", "CrewMember")

    _, blockers = _assess_workforce(runtime, ["ASG-BLOCKED"], planned_activity_id="ACT-1")
    codes = {item.code for item in blockers}

    assert "workforce.assignment-not-ready" in codes
    assert "workforce.competency-requirement-missing" in codes


def test_non_assessment_competency_evidence_is_ignored(monkeypatch):
    runtime = build_runtime()
    objects = [
        OntologyObject(id="ACT-1", type="ActivityInterval", name="Planned activity"),
        OntologyObject(id="PERSON-1", type="CrewMember", name="Crew member"),
        OntologyObject(
            id="ASG-1",
            type="CrewAssignment",
            name="Assignment",
            properties={"status": "READY"},
        ),
        OntologyObject(id="REQ-1", type="CompetencyRequirement", name="Requirement"),
    ]
    for obj in objects:
        runtime.upsert_object(obj)
    _rel(runtime, "assignmentForActivity", "ASG-1", "CrewAssignment", "ACT-1", "ActivityInterval")
    _rel(runtime, "assignmentOf", "ASG-1", "CrewAssignment", "PERSON-1", "CrewMember")
    _rel(
        runtime,
        "assignmentRequiresCompetency",
        "ASG-1",
        "CrewAssignment",
        "REQ-1",
        "CompetencyRequirement",
    )

    wrong_evidence = OntologyObject(id="WO-1", type="WorkOrder", name="Not an assessment")
    original_reverse = runtime.reverse_neighbors

    def reverse_neighbors(object_id: str, relationship_type: str | None = None):
        if object_id == "REQ-1" and relationship_type == "assessmentAgainstRequirement":
            return [wrong_evidence]
        return original_reverse(object_id, relationship_type)

    monkeypatch.setattr(runtime, "reverse_neighbors", reverse_neighbors)

    _, blockers = _assess_workforce(runtime, ["ASG-1"], planned_activity_id="ACT-1")

    assert "workforce.competency-not-demonstrated" in {item.code for item in blockers}


def test_supply_requires_material_identity_on_inventory_and_requirement():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="INV-NO-MATERIAL",
            type="InventoryPosition",
            name="Inventory without material identity",
            properties={"onHandQuantity": 1.0, "shortfallQuantity": 0.0},
        )
    )
    with pytest.raises(ValueError, match="INV-NO-MATERIAL is missing materialNumber"):
        _assess_supply(runtime, [], ["INV-NO-MATERIAL"], rig_id="RIG-1")

    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="REQ-NO-MATERIAL",
            type="MaterialRequirement",
            name="Requirement without material identity",
            properties={"status": "READY"},
        )
    )
    with pytest.raises(ValueError, match="REQ-NO-MATERIAL is missing materialNumber"):
        _assess_supply(runtime, ["REQ-NO-MATERIAL"], [], rig_id="RIG-1")


def test_supply_at_risk_and_missing_inventory_are_explicit():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="REQ-AT-RISK",
            type="MaterialRequirement",
            name="At-risk mud material",
            properties={"status": "AT_RISK", "materialNumber": "MUD-X"},
        )
    )

    _, blockers = _assess_supply(runtime, ["REQ-AT-RISK"], [], rig_id="RIG-1")
    codes = {item.code for item in blockers}

    assert "supply.requirement-at-risk" in codes
    assert "supply.inventory-missing" in codes


def test_supply_not_ready_branch_is_explicit():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="REQ-BLOCKED",
            type="MaterialRequirement",
            name="Blocked critical spare",
            properties={"status": "BLOCKED", "materialNumber": "SPARE-X"},
        )
    )

    _, blockers = _assess_supply(runtime, ["REQ-BLOCKED"], [], rig_id="RIG-1")
    codes = {item.code for item in blockers}

    assert "supply.requirement-not-ready" in codes
    assert "supply.inventory-missing" in codes
