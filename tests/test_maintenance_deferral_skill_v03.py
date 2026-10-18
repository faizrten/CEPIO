from __future__ import annotations

import pytest

from cepio.bootstrap import build_runtime
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from cepio.runtime import AuthorizationError
from cepio.skill_preflight import (
    SkillAuthorityContract,
    SkillGraphPathRequirement,
    SkillGraphPathStep,
    SkillPreflightSpec,
    evaluate_skill_preflight,
)


CORE = "https://cepio.org/ontology/core#"
IND = "https://cepio.org/ontology/industrial#"
REL = "https://cepio.org/ontology/reliability#"
PERF = "https://cepio.org/ontology/performance#"


def maintenance_deferral_skill_spec() -> SkillPreflightSpec:
    return SkillPreflightSpec(
        skill_id="cepio.skill.maintenance.assess-maintenance-deferral",
        binding_id="test-maintenance-deferral-v0.3",
        object_types={
            "Asset": CORE + "Asset",
            "Equipment": IND + "Equipment",
            "ConditionObservation": REL + "ConditionObservation",
            "WorkOrder": IND + "WorkOrder",
            "FailureEvent": REL + "FailureEvent",
            "FailureMode": REL + "FailureMode",
            "Risk": CORE + "Risk",
            "ProductionExposure": PERF + "ProductionExposure",
        },
        relationships={
            "hasConditionObservation": REL + "hasConditionObservation",
            "hasWorkOrder": IND + "hasWorkOrder",
            "failureOfEquipment": REL + "failureOfEquipment",
            "hasFailureMode": REL + "hasFailureMode",
            "hasRisk": CORE + "hasRisk",
        },
        functions={
            "calculate-production-exposure": "calculateProductionExposure",
            "evaluate-maintenance-risk": "evaluateMaintenanceDeferralRisk",
        },
        decisions={"maintenance-deferral-decision": "maintenance-deferral-decision"},
        actions={"defer-work-order": "DeferWorkOrder"},
        evidence_types={
            "Equipment",
            "ConditionObservation",
            "WorkOrder",
            "FailureEvent",
            "FailureMode",
            "Risk",
        },
        graph_paths=[
            SkillGraphPathRequirement(
                id="condition-evidence",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasConditionObservation",
                        target_type="ConditionObservation",
                    )
                ],
            ),
            SkillGraphPathRequirement(
                id="maintenance-item",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasWorkOrder",
                        target_type="WorkOrder",
                    )
                ],
            ),
            SkillGraphPathRequirement(
                id="risk-context",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasRisk",
                        target_type="Risk",
                    )
                ],
            ),
            SkillGraphPathRequirement(
                id="failure-history",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="failureOfEquipment",
                        direction="in",
                        target_type="FailureEvent",
                    ),
                    SkillGraphPathStep(
                        relationship="hasFailureMode",
                        target_type="FailureMode",
                    ),
                ],
            ),
        ],
        authority=SkillAuthorityContract(
            recommend=True,
            propose_decision=True,
            execute_actions=set(),
            approval_required_for={"defer-work-order"},
        ),
    )


def seed_deferral_case():
    runtime = build_runtime()
    equipment = OntologyObject(id="P-101", type="Pump", name="P-101")
    work_order = OntologyObject(
        id="WO-101",
        type="WorkOrder",
        name="Seal replacement",
        properties={"status": "planned", "priority": "high"},
    )
    risk = OntologyObject(
        id="RISK-101",
        type="Risk",
        name="Seal deferral risk",
        properties={
            "currentRiskScore": 0.38,
            "deferralRiskScore": 0.57,
            "maxSupportedDeferralHours": 168.0,
            "hardConstraint": False,
        },
    )
    runtime.upsert_object(equipment)
    runtime.upsert_object(work_order)
    runtime.upsert_object(risk)
    runtime.add_relationship(
        Relationship(
            type="hasWorkOrder",
            source=ObjectRef(id=equipment.id, type=equipment.type),
            target=ObjectRef(id=work_order.id, type=work_order.type),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="hasRisk",
            source=ObjectRef(id=equipment.id, type=equipment.type),
            target=ObjectRef(id=risk.id, type=risk.type),
        )
    )
    return runtime


def test_recommender_is_ready_for_second_bound_skill():
    runtime = build_runtime()
    result = evaluate_skill_preflight(
        runtime,
        maintenance_deferral_skill_spec(),
        actor_id="skill-agent-1",
        actor_roles={"ai_agent_recommender"},
    )

    assert result.status == "READY"
    assert result.blockers == []
    assert any(check.code == "ACTION_HANDOFF_ENFORCED" for check in result.checks)
    assert sum(check.code == "GRAPH_PATH_REACHABLE" for check in result.checks) == 4


def test_auditor_and_over_authorized_manager_fail_closed():
    runtime = build_runtime()

    auditor = evaluate_skill_preflight(
        runtime,
        maintenance_deferral_skill_spec(),
        actor_id="audit-1",
        actor_roles={"auditor"},
    )
    manager = evaluate_skill_preflight(
        runtime,
        maintenance_deferral_skill_spec(),
        actor_id="manager-1",
        actor_roles={"maintenance_manager"},
    )

    assert auditor.status == "BLOCKED"
    auditor_codes = {check.code for check in auditor.blockers}
    assert "FUNCTION_NOT_AUTHORIZED" in auditor_codes
    assert "DECISION_NOT_AUTHORIZED" in auditor_codes
    assert "ACTION_NOT_RECOMMENDABLE" in auditor_codes

    assert manager.status == "BLOCKED"
    assert any(check.code == "ACTOR_EXCEEDS_SKILL_AUTHORITY" for check in manager.blockers)


def test_deferral_risk_function_interprets_governed_risk_without_inventing_model():
    runtime = seed_deferral_case()

    assessment = runtime.call_function(
        "evaluateMaintenanceDeferralRisk",
        equipment_id="P-101",
        work_order_id="WO-101",
        risk_id="RISK-101",
        proposed_deferral_hours=120,
    )

    assert assessment.current_risk_score == 0.38
    assert assessment.deferral_risk_score == 0.57
    assert assessment.max_supported_deferral_hours == 168.0
    assert assessment.within_supported_window is True
    assert assessment.hard_constraint is False

    beyond_window = runtime.call_function(
        "evaluateMaintenanceDeferralRisk",
        equipment_id="P-101",
        work_order_id="WO-101",
        risk_id="RISK-101",
        proposed_deferral_hours=240,
    )
    assert beyond_window.within_supported_window is False


def test_deferral_risk_function_fails_closed_without_linked_risk():
    runtime = seed_deferral_case()
    other = OntologyObject(
        id="RISK-OTHER",
        type="Risk",
        name="Unrelated risk",
        properties={
            "currentRiskScore": 0.1,
            "deferralRiskScore": 0.2,
            "maxSupportedDeferralHours": 720.0,
        },
    )
    runtime.upsert_object(other)

    with pytest.raises(ValueError, match="not linked"):
        runtime.call_function(
            "evaluateMaintenanceDeferralRisk",
            equipment_id="P-101",
            work_order_id="WO-101",
            risk_id="RISK-OTHER",
            proposed_deferral_hours=24,
        )


def test_named_deferral_decision_is_work_order_scoped():
    runtime = seed_deferral_case()
    saved = runtime.save_decision(
        Decision(
            decision_type="maintenance-deferral-decision",
            subject=ObjectRef(id="WO-101", type="WorkOrder"),
            problem="Can planned seal replacement be deferred to the outage?",
            recommendation="Defer only within the supported risk window.",
            recommended_action="DeferWorkOrder",
            created_by="skill-agent-1",
        )
    )
    assert saved.decision_type == "maintenance-deferral-decision"
    assert saved.recommended_action == "DeferWorkOrder"

    with pytest.raises(ValueError, match="does not allow subject type"):
        runtime.save_decision(
            Decision(
                decision_type="maintenance-deferral-decision",
                subject=ObjectRef(id="P-101", type="Pump"),
                problem="Wrong subject",
                recommendation="Do not persist",
                recommended_action="DeferWorkOrder",
            )
        )


def test_deferral_action_preserves_recommend_before_act_boundary_and_audit_causality():
    runtime = seed_deferral_case()
    decision = runtime.save_decision(
        Decision(
            decision_type="maintenance-deferral-decision",
            subject=ObjectRef(id="WO-101", type="WorkOrder"),
            problem="Deferral decision",
            recommendation="Defer to planned outage",
            recommended_action="DeferWorkOrder",
            created_by="skill-agent-1",
        )
    )

    with pytest.raises(AuthorizationError) as exc:
        runtime.execute_action(
            ActionRequest(
                action_type="DeferWorkOrder",
                target=ObjectRef(id="WO-101", type="WorkOrder"),
                actor_id="skill-agent-1",
                actor_roles={"ai_agent_recommender"},
                parameters={"reason": "planned outage", "until": "2026-11-01"},
                decision_id=decision.id,
            )
        )
    assert exc.value.result is not None
    assert exc.value.result.status.value == "rejected"

    executed = runtime.execute_action(
        ActionRequest(
            action_type="DeferWorkOrder",
            target=ObjectRef(id="WO-101", type="WorkOrder"),
            actor_id="manager-1",
            actor_roles={"maintenance_manager"},
            parameters={"reason": "planned outage", "until": "2026-11-01"},
            decision_id=decision.id,
        )
    )
    assert executed.status.value == "executed"
    assert runtime.get_object("WO-101").properties["status"] == "deferred"
    audits = runtime.audits_for_action(executed.action_id)
    assert audits
    assert audits[-1].decision_id == decision.id
