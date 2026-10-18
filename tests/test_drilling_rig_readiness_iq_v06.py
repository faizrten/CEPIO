from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_rig_readiness_iq import (
    DRILLING_RIG_READINESS_IQ_PACK,
    ReadinessDimension,
    RigReadinessStatus,
)
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from cepio.runtime import AuthorizationError


ASSESSMENT_TIME = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def _runtime_with_pack():
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [DRILLING_RIG_READINESS_IQ_PACK])
    return runtime


def _rel(runtime, rel_type: str, source_id: str, source_type: str, target_id: str, target_type: str):
    runtime.add_relationship(
        Relationship(
            type=rel_type,
            source=ObjectRef(id=source_id, type=source_type),
            target=ObjectRef(id=target_id, type=target_type),
        )
    )


def _seed_ready_runtime():
    runtime = _runtime_with_pack()
    objects = [
        OntologyObject(id="RIG-1", type="OperatingRig", name="Rig 1"),
        OntologyObject(
            id="ACT-PLAN",
            type="ActivityInterval",
            name="Drill out shoe",
            properties={"status": "PLANNED"},
        ),
        OntologyObject(
            id="EQ-TD",
            type="DrillingEquipment",
            name="Top drive",
            properties={"status": "READY"},
        ),
        OntologyObject(
            id="WO-CLOSED",
            type="WorkOrder",
            name="Completed top-drive inspection",
            properties={"status": "CLOSED", "readinessBlocking": True},
        ),
        OntologyObject(
            id="BOP-1",
            type="BlowoutPreventer",
            name="BOP stack",
            properties={"status": "READY"},
        ),
        OntologyObject(
            id="TEST-BOP",
            type="WellControlTest",
            name="BOP pressure test",
            properties={
                "status": "PASSED",
                "validTo": "2026-10-20T00:00:00+00:00",
            },
        ),
        OntologyObject(
            id="ASG-DRILLER",
            type="CrewAssignment",
            name="Driller tour assignment",
            properties={"status": "READY"},
        ),
        OntologyObject(id="PERSON-1", type="CrewMember", name="Driller 1"),
        OntologyObject(
            id="REQ-WC",
            type="CompetencyRequirement",
            name="Well-control competency requirement",
        ),
        OntologyObject(
            id="ASSESS-WC",
            type="CompetencyAssessment",
            name="Driller competency assessment",
            properties={"competencyLevel": "QUALIFIED"},
        ),
        OntologyObject(
            id="MAT-BARITE",
            type="MaterialRequirement",
            name="Barite contingency requirement",
            properties={"status": "READY", "materialNumber": "BARITE"},
        ),
        OntologyObject(
            id="INV-BARITE",
            type="InventoryPosition",
            name="Rig barite inventory",
            properties={
                "materialNumber": "BARITE",
                "onHandQuantity": 120.0,
                "shortfallQuantity": 0.0,
            },
        ),
    ]
    for obj in objects:
        runtime.upsert_object(obj)

    _rel(runtime, "activityOnRig", "ACT-PLAN", "ActivityInterval", "RIG-1", "OperatingRig")
    _rel(runtime, "hasWorkOrder", "EQ-TD", "DrillingEquipment", "WO-CLOSED", "WorkOrder")
    _rel(runtime, "testsWellControlEquipment", "TEST-BOP", "WellControlTest", "BOP-1", "BlowoutPreventer")
    _rel(runtime, "assignmentForActivity", "ASG-DRILLER", "CrewAssignment", "ACT-PLAN", "ActivityInterval")
    _rel(runtime, "assignmentOf", "ASG-DRILLER", "CrewAssignment", "PERSON-1", "CrewMember")
    _rel(runtime, "assignmentRequiresCompetency", "ASG-DRILLER", "CrewAssignment", "REQ-WC", "CompetencyRequirement")
    _rel(runtime, "assessmentAgainstRequirement", "ASSESS-WC", "CompetencyAssessment", "REQ-WC", "CompetencyRequirement")
    _rel(runtime, "assessmentOfPerson", "ASSESS-WC", "CompetencyAssessment", "PERSON-1", "CrewMember")
    _rel(runtime, "stockedAtAsset", "INV-BARITE", "InventoryPosition", "RIG-1", "OperatingRig")
    return runtime


def _assess(runtime, **overrides):
    payload = {
        "rig_id": "RIG-1",
        "planned_activity_id": "ACT-PLAN",
        "assessment_time": ASSESSMENT_TIME,
        "equipment_ids": ["EQ-TD", "BOP-1"],
        "well_control_test_ids": ["TEST-BOP"],
        "crew_assignment_ids": ["ASG-DRILLER"],
        "material_requirement_ids": ["MAT-BARITE"],
        "inventory_position_ids": ["INV-BARITE"],
    }
    payload.update(overrides)
    return runtime.call_function("assessRigReadiness", **payload)


def test_rig_readiness_iq_is_not_a_core_default():
    runtime = build_runtime()
    assert runtime.has_function("assessRigReadiness") is False
    assert runtime.has_decision("rig-readiness-intervention-recommendation") is False
    assert runtime.has_action("CreateReadinessException") is False


def test_pack_installs_only_explicit_rig_readiness_capabilities():
    runtime = _runtime_with_pack()
    assert runtime.has_function("assessRigReadiness") is True
    assert runtime.has_decision("rig-readiness-intervention-recommendation") is True
    assert runtime.has_action("CreateReadinessException") is True
    assert runtime.industry_iq_packs == {"cepio.iq.drilling.rig-readiness": "0.1.0"}


def test_ready_result_requires_cross_functional_evidence():
    result = _assess(_seed_ready_runtime())

    assert result.status == RigReadinessStatus.ready
    assert result.blockers == []
    assert {item.dimension for item in result.dimensions} == {
        ReadinessDimension.equipment,
        ReadinessDimension.well_control,
        ReadinessDimension.workforce,
        ReadinessDimension.supply,
    }
    assert {item.status for item in result.dimensions} == {RigReadinessStatus.ready}
    assert {
        "RIG-1",
        "ACT-PLAN",
        "EQ-TD",
        "BOP-1",
        "TEST-BOP",
        "ASG-DRILLER",
        "PERSON-1",
        "REQ-WC",
        "ASSESS-WC",
        "MAT-BARITE",
        "INV-BARITE",
    }.issubset(set(result.evidence_ids))


def test_degraded_but_nonblocking_equipment_is_conditionally_ready():
    runtime = _seed_ready_runtime()
    equipment = runtime.get_object("EQ-TD")
    equipment.properties["status"] = "DEGRADED"
    runtime.upsert_object(equipment, expected_version=equipment.version)

    result = _assess(runtime)

    assert result.status == RigReadinessStatus.conditionally_ready
    assert [item.code for item in result.blockers] == ["equipment.degraded"]
    assert result.blockers[0].severity == "advisory"


def test_blocking_maintenance_makes_rig_not_ready():
    runtime = _seed_ready_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="WO-BLOCK",
            type="WorkOrder",
            name="Repair top drive cooling",
            properties={"status": "OPEN", "readinessBlocking": True},
        )
    )
    _rel(runtime, "hasWorkOrder", "EQ-TD", "DrillingEquipment", "WO-BLOCK", "WorkOrder")

    result = _assess(runtime)

    assert result.status == RigReadinessStatus.not_ready
    assert "equipment.blocking-work-order" in {item.code for item in result.blockers}


def test_active_work_order_without_readiness_impact_fails_closed_as_blocker():
    runtime = _seed_ready_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="WO-UNKNOWN",
            type="WorkOrder",
            name="Unclassified maintenance exposure",
            properties={"status": "OPEN"},
        )
    )
    _rel(runtime, "hasWorkOrder", "EQ-TD", "DrillingEquipment", "WO-UNKNOWN", "WorkOrder")

    result = _assess(runtime)

    assert result.status == RigReadinessStatus.not_ready
    assert "equipment.work-order-impact-unknown" in {item.code for item in result.blockers}


def test_failed_or_expired_well_control_evidence_blocks_readiness():
    runtime = _seed_ready_runtime()
    test = runtime.get_object("TEST-BOP")
    test.properties["status"] = "FAILED"
    test.properties["validTo"] = "2026-10-18T11:00:00+00:00"
    runtime.upsert_object(test, expected_version=test.version)

    result = _assess(runtime)
    codes = {item.code for item in result.blockers}

    assert result.status == RigReadinessStatus.not_ready
    assert "well-control.test-not-passed" in codes
    assert "well-control.test-expired" in codes


def test_missing_well_control_validity_blocks_readiness():
    runtime = _seed_ready_runtime()
    test = runtime.get_object("TEST-BOP")
    test.properties.pop("validTo")
    runtime.upsert_object(test, expected_version=test.version)

    result = _assess(runtime)

    assert result.status == RigReadinessStatus.not_ready
    assert "well-control.validity-missing" in {item.code for item in result.blockers}


def test_unqualified_assigned_person_blocks_readiness():
    runtime = _seed_ready_runtime()
    assessment = runtime.get_object("ASSESS-WC")
    assessment.properties["competencyLevel"] = "NOT_QUALIFIED"
    runtime.upsert_object(assessment, expected_version=assessment.version)

    result = _assess(runtime)

    assert result.status == RigReadinessStatus.not_ready
    assert "workforce.competency-not-demonstrated" in {
        item.code for item in result.blockers
    }


def test_material_shortfall_or_wrong_location_blocks_readiness():
    runtime = _seed_ready_runtime()
    inventory = runtime.get_object("INV-BARITE")
    inventory.properties["shortfallQuantity"] = 10.0
    runtime.upsert_object(inventory, expected_version=inventory.version)

    result = _assess(runtime)

    assert result.status == RigReadinessStatus.not_ready
    assert "supply.stockout-or-wrong-location" in {item.code for item in result.blockers}


def test_required_dimension_without_evidence_is_rejected_before_reasoning():
    runtime = _seed_ready_runtime()

    with pytest.raises(ValueError, match="well_control readiness evidence is required"):
        _assess(runtime, well_control_test_ids=[])
    with pytest.raises(ValueError, match="supply inventory readiness evidence is required"):
        _assess(runtime, inventory_position_ids=[])


def test_optional_dimension_can_be_excluded_explicitly():
    runtime = _seed_ready_runtime()
    result = _assess(
        runtime,
        required_dimensions={
            ReadinessDimension.equipment,
            ReadinessDimension.workforce,
        },
        well_control_test_ids=[],
        material_requirement_ids=[],
        inventory_position_ids=[],
    )

    assert result.status == RigReadinessStatus.ready
    assert {item.dimension for item in result.dimensions} == {
        ReadinessDimension.equipment,
        ReadinessDimension.workforce,
    }


def test_planned_activity_must_be_scoped_to_the_rig():
    runtime = _seed_ready_runtime()
    runtime.upsert_object(OntologyObject(id="RIG-2", type="OperatingRig", name="Rig 2"))

    with pytest.raises(ValueError, match="is not linked to rig RIG-2"):
        _assess(runtime, rig_id="RIG-2")


def test_malformed_temporal_and_supply_evidence_fails_closed():
    runtime = _seed_ready_runtime()
    test = runtime.get_object("TEST-BOP")
    test.properties["validTo"] = "not-a-date"
    runtime.upsert_object(test, expected_version=test.version)
    with pytest.raises(ValueError, match="validTo must be an ISO-8601 timestamp"):
        _assess(runtime)

    runtime = _seed_ready_runtime()
    inventory = runtime.get_object("INV-BARITE")
    inventory.properties["onHandQuantity"] = "120"
    runtime.upsert_object(inventory, expected_version=inventory.version)
    with pytest.raises(ValueError, match="onHandQuantity must be numeric"):
        _assess(runtime)


def test_readiness_decision_recommends_before_human_action():
    runtime = _seed_ready_runtime()
    result = _assess(runtime)
    assert result.status == RigReadinessStatus.ready

    decision = runtime.save_decision(
        Decision(
            decision_type="rig-readiness-intervention-recommendation",
            subject=ObjectRef(id="RIG-1", type="OperatingRig"),
            problem="Should the planned operation be released with an exception?",
            recommendation="Create a governed readiness exception for review.",
            recommended_action="CreateReadinessException",
            created_by="readiness-agent-1",
        )
    )
    request = ActionRequest(
        action_type="CreateReadinessException",
        target=ObjectRef(id="RIG-1", type="OperatingRig"),
        actor_id="readiness-agent-1",
        actor_roles={"rig_readiness_recommender"},
        parameters={
            "reason": "human review requested for readiness deviation",
            "planned_activity_id": "ACT-PLAN",
            "blocker_codes": ["equipment.degraded"],
        },
        decision_id=decision.id,
    )

    with pytest.raises(AuthorizationError):
        runtime.execute_action(request)

    executed = runtime.execute_action(
        request.model_copy(
            update={"actor_id": "rig-manager-1", "actor_roles": {"rig_manager"}}
        )
    )
    assert executed.status.value == "executed"
    exception_id = str(executed.effects["readiness_exception_id"])
    exception = runtime.get_object(exception_id)
    assert exception.type == "WorkItem"
    assert exception.properties["workItemKind"] == "rig-readiness-exception"
    assert runtime.neighbors(exception_id, "impacts")[0].id == "RIG-1"
    assert runtime.neighbors(exception_id, "dependsOn")[0].id == "ACT-PLAN"
