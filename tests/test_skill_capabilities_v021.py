import pytest
from pydantic import ValidationError

from cepio.bootstrap import build_runtime
from cepio.mcp import MCPFacade
from cepio.model import Decision, ObjectRef, OntologyObject, Relationship
from cepio.runtime import AuthorizationError


def test_equipment_degradation_semantics_are_canonical_and_composable():
    runtime = build_runtime()
    registry = runtime.type_registry
    assert registry is not None

    assert registry.is_declared_type("ConditionObservation")
    assert registry.is_declared_type("ProductionExposure")
    assert registry.is_declared_relationship("hasConditionObservation")
    assert registry.is_a("ConditionSignal", "ConditionObservation")

    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))
    runtime.upsert_object(OntologyObject(id="COND-1", type="ConditionSignal", name="K-201 vibration"))
    runtime.add_relationship(
        Relationship(
            type="hasConditionObservation",
            source=ObjectRef(id="K-201", type="Compressor"),
            target=ObjectRef(id="COND-1", type="ConditionSignal"),
        )
    )

    observations = runtime.neighbors("K-201", "hasConditionObservation")
    assert [item.id for item in observations] == ["COND-1"]


def test_production_exposure_is_a_registered_typed_function():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))

    assert runtime.has_function("calculateProductionExposure")
    exposure = runtime.call_function(
        "calculateProductionExposure",
        asset_id="K-201",
        hours=2.5,
        production_rate_per_hour=120.0,
    )
    assert exposure == 300.0

    with pytest.raises(ValidationError):
        runtime.call_function(
            "calculateProductionExposure",
            asset_id="K-201",
            hours=-1,
            production_rate_per_hour=120.0,
        )


def test_mcp_boundary_exposes_declared_condition_and_failure_evidence():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={"criticality": "high", "operatingState": "running"},
        )
    )
    runtime.upsert_object(
        OntologyObject(
            id="COND-1",
            type="ConditionSignal",
            name="K-201 vibration",
            properties={"value": 7.2, "unit": "mm/s"},
        )
    )
    runtime.upsert_object(OntologyObject(id="FEV-1", type="FailureEvent", name="Prior bearing event"))
    runtime.upsert_object(OntologyObject(id="FM-1", type="FailureMode", name="Bearing degradation"))
    runtime.add_relationship(
        Relationship(
            type="hasConditionObservation",
            source=ObjectRef(id="K-201", type="Compressor"),
            target=ObjectRef(id="COND-1", type="ConditionSignal"),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="failureOfEquipment",
            source=ObjectRef(id="FEV-1", type="FailureEvent"),
            target=ObjectRef(id="K-201", type="Compressor"),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="hasFailureMode",
            source=ObjectRef(id="FEV-1", type="FailureEvent"),
            target=ObjectRef(id="FM-1", type="FailureMode"),
        )
    )

    recommender = MCPFacade(
        runtime,
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
    )
    visible = recommender.call_tool(
        "cepio_neighbors",
        {"object_id": "K-201", "relationship_type": "hasConditionObservation"},
    )
    assert [item["id"] for item in visible["objects"]] == ["COND-1"]

    failures = recommender.call_tool(
        "cepio_neighbors",
        {"object_id": "K-201", "relationship_type": "failureOfEquipment", "direction": "in"},
    )
    assert [item["id"] for item in failures["objects"]] == ["FEV-1"]
    modes = recommender.call_tool(
        "cepio_neighbors",
        {"object_id": "FEV-1", "relationship_type": "hasFailureMode", "direction": "out"},
    )
    assert [item["id"] for item in modes["objects"]] == ["FM-1"]


def test_mcp_boundary_enforces_function_policy():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))
    recommender = MCPFacade(runtime, actor_id="agent-1", actor_roles={"ai_agent_recommender"})
    result = recommender.call_tool(
        "cepio_call_function",
        {
            "function": "calculateProductionExposure",
            "arguments": {
                "asset_id": "K-201",
                "hours": 2.5,
                "production_rate_per_hour": 120.0,
            },
        },
    )
    assert result == {"result": 300.0}

    auditor = MCPFacade(runtime, actor_id="audit-1", actor_roles={"auditor"})
    with pytest.raises(AuthorizationError, match="not authorized to call function"):
        auditor.call_tool(
            "cepio_call_function",
            {
                "function": "calculateProductionExposure",
                "arguments": {
                    "asset_id": "K-201",
                    "hours": 2.5,
                    "production_rate_per_hour": 120.0,
                },
            },
        )


def test_mcp_decision_proposal_is_authorized_and_action_remains_recommend_only():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            interfaces={"MaintainableAsset"},
            properties={"criticality": "high", "operatingState": "running"},
        )
    )
    recommender = MCPFacade(
        runtime,
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
    )

    decision = recommender.call_tool(
        "cepio_save_decision",
        {
            "decision_type": "maintenance-intervention-recommendation",
            "subject_id": "K-201",
            "subject_type": "Compressor",
            "problem": "Increasing vibration",
            "observations": ["Condition trend increased for three days"],
            "recommendation": "Create a maintenance work order for inspection planning",
            "recommended_action": "CreateWorkOrder",
            "confidence": 0.82,
        },
    )
    assert decision["decision_type"] == "maintenance-intervention-recommendation"
    assert decision["created_by"] == "agent-1"

    result = recommender.call_tool(
        "cepio_execute_action",
        {
            "action_type": "CreateWorkOrder",
            "target_id": "K-201",
            "target_type": "Compressor",
            "parameters": {},
            "decision_id": decision["id"],
        },
    )
    assert result["status"] == "rejected"
    assert runtime.neighbors("K-201", "hasWorkOrder") == []
    audits = runtime.all_audits()
    assert audits[-1].decision_id == decision["id"]
    assert audits[-1].policy_effect.value == "recommend_only"

    auditor = MCPFacade(runtime, actor_id="audit-1", actor_roles={"auditor"})
    with pytest.raises(AuthorizationError, match="not authorized to propose decision"):
        auditor.call_tool(
            "cepio_save_decision",
            {
                "decision_type": "maintenance-intervention-recommendation",
                "subject_id": "K-201",
                "subject_type": "Compressor",
                "problem": "Increasing vibration",
                "recommendation": "Create a work order",
                "recommended_action": "CreateWorkOrder",
            },
        )


def test_maintenance_intervention_recommendation_is_registered_and_typed():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))

    assert runtime.has_decision("maintenance-intervention-recommendation")
    definition = runtime.get_decision_definition("maintenance-intervention-recommendation")
    assert definition.allowed_subject_types == {"Equipment"}
    assert definition.allowed_actions == {"CreateWorkOrder", "CreateInspection", "EscalateRisk"}

    decision = runtime.save_decision(
        Decision(
            decision_type="maintenance-intervention-recommendation",
            subject=ObjectRef(id="K-201", type="Compressor"),
            problem="Increasing vibration",
            observations=["Vibration trend increased over three days"],
            recommendation="Plan an inspection before the next operating window",
            recommended_action="CreateInspection",
            confidence=0.8,
            created_by="reliability-agent",
        )
    )
    assert decision.decision_type == "maintenance-intervention-recommendation"
    assert runtime.get_decision(decision.id).recommended_action == "CreateInspection"


def test_named_decision_rejects_wrong_subject_or_action():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="DOC-1", type="Document", name="Procedure"))
    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))

    with pytest.raises(ValueError, match="does not allow subject type"):
        runtime.save_decision(
            Decision(
                decision_type="maintenance-intervention-recommendation",
                subject=ObjectRef(id="DOC-1", type="Document"),
                problem="Not an equipment decision",
                recommendation="No action",
            )
        )

    with pytest.raises(ValueError, match="does not allow action"):
        runtime.save_decision(
            Decision(
                decision_type="maintenance-intervention-recommendation",
                subject=ObjectRef(id="K-201", type="Compressor"),
                problem="Increasing vibration",
                recommendation="Attempt an unrelated action",
                recommended_action="ApproveMaintenanceDeferral",
            )
        )


def test_legacy_untyped_decisions_remain_backward_compatible():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))

    stored = runtime.save_decision(
        Decision(
            subject=ObjectRef(id="K-201", type="Compressor"),
            problem="Legacy decision",
            recommendation="Continue monitoring",
        )
    )
    assert stored.decision_type is None
