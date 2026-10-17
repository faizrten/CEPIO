import pytest

from cepio.bootstrap import build_runtime
from cepio.model import Decision, ObjectRef, OntologyObject, Relationship


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

    with pytest.raises(Exception):
        runtime.call_function(
            "calculateProductionExposure",
            asset_id="K-201",
            hours=-1,
            production_rate_per_hour=120.0,
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
