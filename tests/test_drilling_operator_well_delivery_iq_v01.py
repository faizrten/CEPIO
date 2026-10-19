from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_operator_well_delivery_iq import (
    DRILLING_OPERATOR_WELL_DELIVERY_IQ_PACK,
    WellDeliveryStatus,
    _is_a,
    _normalized_property,
    _require_scoped_approved_plan,
    _require_type,
    _require_well_target,
)
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from cepio.runtime import AuthorizationError, PreconditionsError


AT = datetime(2026, 10, 19, 3, 0, tzinfo=timezone.utc)


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


def _runtime_with_pack():
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [DRILLING_OPERATOR_WELL_DELIVERY_IQ_PACK])
    return runtime


def _seed():
    runtime = _runtime_with_pack()
    objects = [
        OntologyObject(id="WELL-1", type="Well", name="Well 1"),
        OntologyObject(id="WELL-2", type="Well", name="Well 2"),
        OntologyObject(
            id="PLAN-1",
            type="OperationalPlan",
            name="Approved well plan",
            properties={"status": "APPROVED", "wellId": "WELL-1"},
        ),
        OntologyObject(
            id="PLAN-2",
            type="OperationalPlan",
            name="Other well plan",
            properties={"status": "APPROVED", "wellId": "WELL-2"},
        ),
        OntologyObject(
            id="ACT-1",
            type="ActivityInterval",
            name="Drill 12 1/4 inch section",
            properties={"status": "IN_PROGRESS"},
        ),
        OntologyObject(
            id="ACT-2",
            type="ActivityInterval",
            name="Circulate bottoms up",
            properties={"status": "COMPLETED"},
        ),
    ]
    for obj in objects:
        runtime.upsert_object(obj)
    _rel(runtime, "activityForWell", "ACT-1", "ActivityInterval", "WELL-1", "Well")
    _rel(runtime, "activityForWell", "ACT-2", "ActivityInterval", "WELL-1", "Well")
    return runtime


def _assess(runtime, **overrides):
    payload = {
        "well_id": "WELL-1",
        "approved_plan_id": "PLAN-1",
        "assessment_time": AT,
        "activity_ids": ["ACT-1", "ACT-2"],
        "plan_deviation_ids": [],
        "risk_ids": [],
    }
    payload.update(overrides)
    return runtime.call_function("assessOperatorWellDelivery", **payload)


def _add_deviation(
    runtime,
    *,
    deviation_id: str = "DEV-1",
    severity: str = "ADVISORY",
    status: str = "OPEN",
    plan_id: str = "PLAN-1",
    impact_id: str = "ACT-1",
    impact_type: str = "ActivityInterval",
):
    runtime.upsert_object(
        OntologyObject(
            id=deviation_id,
            type="PlanDeviation",
            name=f"Deviation {deviation_id}",
            properties={"status": status, "severity": severity},
        )
    )
    _rel(runtime, "deviationFromPlan", deviation_id, "PlanDeviation", plan_id, "OperationalPlan")
    _rel(runtime, "impacts", deviation_id, "PlanDeviation", impact_id, impact_type)
    return deviation_id


def _add_risk(
    runtime,
    *,
    risk_id: str = "RISK-1",
    severity: str = "HIGH",
    status: str = "OPEN",
    owner_id: str = "WELL-1",
    owner_type: str = "Well",
):
    runtime.upsert_object(
        OntologyObject(
            id=risk_id,
            type="Risk",
            name=f"Risk {risk_id}",
            properties={"status": status, "severity": severity},
        )
    )
    _rel(runtime, "hasRisk", owner_id, owner_type, risk_id, "Risk")
    return risk_id


def test_operator_well_delivery_iq_is_not_core_default():
    runtime = build_runtime()
    assert runtime.has_function("assessOperatorWellDelivery") is False
    assert runtime.has_decision("operator-well-delivery-intervention-recommendation") is False
    assert runtime.has_action("InitiateWellPlanRevision") is False


def test_pack_installs_explicit_operator_capabilities_only():
    runtime = _runtime_with_pack()
    assert runtime.has_function("assessOperatorWellDelivery") is True
    assert runtime.has_decision("operator-well-delivery-intervention-recommendation") is True
    assert runtime.has_action("InitiateWellPlanRevision") is True
    assert runtime.industry_iq_packs == {"cepio.iq.drilling.operator-well-delivery": "0.1.0"}


def test_on_plan_requires_approved_plan_and_scoped_execution_evidence():
    result = _assess(_seed())
    assert result.status == WellDeliveryStatus.on_plan
    assert result.findings == []
    assert result.evidence_ids == ["ACT-1", "ACT-2", "PLAN-1", "WELL-1"]
    assert "aligned" in result.recommendation


def test_advisory_plan_deviation_makes_delivery_at_risk():
    runtime = _seed()
    deviation_id = _add_deviation(runtime, severity="ADVISORY")
    result = _assess(runtime, plan_deviation_ids=[deviation_id])
    assert result.status == WellDeliveryStatus.at_risk
    assert [item.code for item in result.findings] == ["plan.active-deviation"]
    assert result.findings[0].severity == "advisory"
    assert deviation_id in result.evidence_ids


def test_material_plan_deviation_requires_operator_intervention():
    runtime = _seed()
    deviation_id = _add_deviation(runtime, severity="MATERIAL")
    result = _assess(runtime, plan_deviation_ids=[deviation_id])
    assert result.status == WellDeliveryStatus.intervention_required
    assert result.findings[0].severity == "blocking"
    assert "plan revision" in result.recommendation.lower()


def test_high_well_risk_requires_operator_intervention():
    runtime = _seed()
    risk_id = _add_risk(runtime, severity="HIGH")
    result = _assess(runtime, risk_ids=[risk_id])
    assert result.status == WellDeliveryStatus.intervention_required
    assert result.findings[0].code == "execution.active-risk"
    assert result.findings[0].severity == "blocking"


def test_medium_activity_scoped_risk_is_advisory():
    runtime = _seed()
    risk_id = _add_risk(
        runtime,
        risk_id="RISK-ACT",
        severity="MEDIUM",
        owner_id="ACT-1",
        owner_type="ActivityInterval",
    )
    result = _assess(runtime, risk_ids=[risk_id])
    assert result.status == WellDeliveryStatus.at_risk
    assert result.findings[0].severity == "advisory"


def test_closed_deviation_and_mitigated_risk_remain_evidence_but_do_not_trigger():
    runtime = _seed()
    deviation_id = _add_deviation(runtime, status="CLOSED", severity="CRITICAL")
    risk_id = _add_risk(runtime, status="MITIGATED", severity="CRITICAL")
    result = _assess(runtime, plan_deviation_ids=[deviation_id], risk_ids=[risk_id])
    assert result.status == WellDeliveryStatus.on_plan
    assert result.findings == []
    assert deviation_id in result.evidence_ids
    assert risk_id in result.evidence_ids


def test_blocked_activity_is_operator_intervention_signal():
    runtime = _seed()
    activity = runtime.get_object("ACT-1")
    activity.properties["status"] = "BLOCKED"
    runtime.upsert_object(activity, expected_version=activity.version)
    result = _assess(runtime)
    assert result.status == WellDeliveryStatus.intervention_required
    assert result.findings[0].code == "execution.activity-blocked"


def test_assessment_requires_timezone_context():
    with pytest.raises(ValueError, match="assessment_time must include timezone context"):
        _assess(_seed(), assessment_time=datetime(2026, 10, 19, 3, 0))


def test_plan_must_be_approved_and_scoped_to_the_assessed_well():
    runtime = _seed()
    plan = runtime.get_object("PLAN-1")
    plan.properties["status"] = "DRAFT"
    runtime.upsert_object(plan, expected_version=plan.version)
    with pytest.raises(ValueError, match="is not approved/current"):
        _assess(runtime)

    runtime = _seed()
    plan = runtime.get_object("PLAN-1")
    plan.properties.pop("wellId")
    runtime.upsert_object(plan, expected_version=plan.version)
    with pytest.raises(ValueError, match="missing governed wellId scope"):
        _assess(runtime)

    runtime = _seed()
    with pytest.raises(ValueError, match="scoped to well WELL-2, not WELL-1"):
        _assess(runtime, approved_plan_id="PLAN-2")


def test_activity_must_be_well_scoped_and_status_normalized():
    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="ACT-OTHER",
            type="ActivityInterval",
            name="Other well activity",
            properties={"status": "ACTIVE"},
        )
    )
    _rel(runtime, "activityForWell", "ACT-OTHER", "ActivityInterval", "WELL-2", "Well")
    with pytest.raises(ValueError, match="is not linked to well WELL-1"):
        _assess(runtime, activity_ids=["ACT-OTHER"])

    runtime = _seed()
    activity = runtime.get_object("ACT-1")
    activity.properties["status"] = "UNKNOWN_STATE"
    runtime.upsert_object(activity, expected_version=activity.version)
    with pytest.raises(ValueError, match="unsupported normalized status"):
        _assess(runtime)


def test_deviation_must_reference_plan_and_assessed_scope():
    runtime = _seed()
    deviation_id = _add_deviation(runtime, plan_id="PLAN-2")
    with pytest.raises(ValueError, match="does not reference approved plan PLAN-1"):
        _assess(runtime, plan_deviation_ids=[deviation_id])

    runtime = _seed()
    deviation_id = _add_deviation(runtime, impact_id="WELL-2", impact_type="Well")
    with pytest.raises(ValueError, match="is not scoped to well WELL-1"):
        _assess(runtime, plan_deviation_ids=[deviation_id])


def test_deviation_status_and_severity_fail_closed_when_unsupported():
    runtime = _seed()
    deviation_id = _add_deviation(runtime, status="PENDING")
    with pytest.raises(ValueError, match="unsupported status PENDING"):
        _assess(runtime, plan_deviation_ids=[deviation_id])

    runtime = _seed()
    deviation_id = _add_deviation(runtime, severity="UNKNOWN")
    with pytest.raises(ValueError, match="unsupported severity UNKNOWN"):
        _assess(runtime, plan_deviation_ids=[deviation_id])


def test_risk_must_be_scoped_and_status_and_severity_supported():
    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="RISK-UNSCOPED",
            type="Risk",
            name="Unscoped risk",
            properties={"status": "OPEN", "severity": "HIGH"},
        )
    )
    with pytest.raises(ValueError, match="not governed by the assessed well/activity scope"):
        _assess(runtime, risk_ids=["RISK-UNSCOPED"])

    runtime = _seed()
    risk_id = _add_risk(runtime, status="PENDING")
    with pytest.raises(ValueError, match="unsupported status PENDING"):
        _assess(runtime, risk_ids=[risk_id])

    runtime = _seed()
    risk_id = _add_risk(runtime, severity="UNKNOWN")
    with pytest.raises(ValueError, match="unsupported severity UNKNOWN"):
        _assess(runtime, risk_ids=[risk_id])


def test_helpers_fail_closed_on_wrong_type_and_missing_normalized_property():
    assert _is_a(_NoRegistryRuntime(), "Well", "Well") is True
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="NOT-WELL", type="WorkItem", name="Wrong type"))
    with pytest.raises(ValueError, match="NOT-WELL is not a Well"):
        _require_type(runtime, "NOT-WELL", "Well")
    with pytest.raises(ValueError, match="missing required normalized status"):
        _normalized_property(
            OntologyObject(id="OBJ-1", type="WorkItem", name="No status"), "status"
        )


def test_plan_revision_is_recommendation_first_and_human_operator_action():
    runtime = _seed()
    risk_id = _add_risk(runtime, severity="HIGH")
    assessment = _assess(runtime, risk_ids=[risk_id])
    assert assessment.status == WellDeliveryStatus.intervention_required

    decision = runtime.save_decision(
        Decision(
            decision_type="operator-well-delivery-intervention-recommendation",
            subject=ObjectRef(id="WELL-1", type="Well"),
            problem="Does current execution require an operator plan revision?",
            recommendation="Initiate governed review of the approved well plan.",
            recommended_action="InitiateWellPlanRevision",
            created_by="operator-iq-agent-1",
        )
    )
    request = ActionRequest(
        action_type="InitiateWellPlanRevision",
        target=ObjectRef(id="WELL-1", type="Well"),
        actor_id="operator-iq-agent-1",
        actor_roles={"operator_well_delivery_recommender"},
        parameters={
            "plan_id": "PLAN-1",
            "rationale": "High execution risk requires operator review.",
            "assessment_status": assessment.status.value,
            "evidence_ids": assessment.evidence_ids,
        },
        decision_id=decision.id,
    )
    with pytest.raises(AuthorizationError):
        runtime.execute_action(request)

    executed = runtime.execute_action(
        request.model_copy(
            update={
                "actor_id": "operator-wellsite-leader-1",
                "actor_roles": {"operator_wellsite_leader"},
            }
        )
    )
    assert executed.status.value == "executed"
    revision_id = str(executed.effects["plan_revision_id"])
    revision = runtime.get_object(revision_id)
    assert revision.type == "PlanRevision"
    assert revision.properties["status"] == "DRAFT"
    assert revision.properties["wellId"] == "WELL-1"
    assert runtime.neighbors(revision_id, "revisesPlan")[0].id == "PLAN-1"
    assert runtime.neighbors(revision_id, "impacts")[0].id == "WELL-1"


def test_plan_revision_action_preconditions_fail_closed():
    runtime = _seed()
    decision = runtime.save_decision(
        Decision(
            decision_type="operator-well-delivery-intervention-recommendation",
            subject=ObjectRef(id="WELL-1", type="Well"),
            problem="Review",
            recommendation="Revise",
            recommended_action="InitiateWellPlanRevision",
            created_by="human-1",
        )
    )
    base = ActionRequest(
        action_type="InitiateWellPlanRevision",
        target=ObjectRef(id="WELL-1", type="Well"),
        actor_id="human-1",
        actor_roles={"operator_drilling_superintendent"},
        parameters={"plan_id": "PLAN-1", "rationale": "Material deviation"},
        decision_id=decision.id,
    )

    with pytest.raises(PreconditionsError, match="Parameter rationale is required"):
        runtime.execute_action(base.model_copy(update={"parameters": {"plan_id": "PLAN-1"}}))
    with pytest.raises(PreconditionsError, match="Parameter plan_id is required"):
        runtime.execute_action(base.model_copy(update={"parameters": {"rationale": "Reason"}}))
    with pytest.raises(PreconditionsError, match="scoped to well WELL-2"):
        runtime.execute_action(
            base.model_copy(update={"parameters": {"plan_id": "PLAN-2", "rationale": "Reason"}})
        )


def test_action_precondition_helpers_cover_wrong_target_and_unknown_plan():
    runtime = _seed()
    target = runtime.get_object("WELL-1")
    request = ActionRequest(
        action_type="InitiateWellPlanRevision",
        target=ObjectRef(id="WELL-1", type="Well"),
        actor_id="human-1",
        actor_roles={"operator_drilling_engineer"},
        parameters={"plan_id": "MISSING-PLAN", "rationale": "Reason"},
    )
    ok, reason = _require_scoped_approved_plan(request, target, runtime)
    assert ok is False
    assert "Unknown CEPIO object" in reason

    wrong_target = OntologyObject(id="NOT-WELL", type="WorkItem", name="Wrong target")
    ok, reason = _require_well_target(request, wrong_target, runtime)
    assert ok is False
    assert reason == "Target must be a Well"
