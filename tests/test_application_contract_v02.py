from __future__ import annotations

import pytest

from cepio.application_contract import (
    CEPIOApplicationService,
    EvidenceReference,
    EvidenceRole,
    ExecutionContext,
    SkillEvaluationStatus,
    SkillExecutorRegistry,
    SkillInvocation,
)
from cepio.bootstrap import build_runtime
from cepio.maintenance_deferral_skill import (
    MAINTENANCE_DEFERRAL_SKILL_ID,
    execute_maintenance_deferral,
    maintenance_deferral_skill_spec,
)
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.runtime import AuthorizationError
from cepio.skill_preflight import SkillRegistry


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
    observation = OntologyObject(
        id="OBS-101",
        type="ConditionObservation",
        name="Seal condition observation",
        properties={"severity": "moderate"},
    )
    for obj in (equipment, work_order, risk, observation):
        runtime.upsert_object(obj)
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
    runtime.add_relationship(
        Relationship(
            type="hasConditionObservation",
            source=ObjectRef(id=equipment.id, type=equipment.type),
            target=ObjectRef(id=observation.id, type=observation.type),
        )
    )
    return runtime


def application_service(runtime, *, bind_executor: bool = True) -> CEPIOApplicationService:
    skills = SkillRegistry(runtime)
    skills.register(maintenance_deferral_skill_spec())
    executors = SkillExecutorRegistry()
    if bind_executor:
        executors.register(MAINTENANCE_DEFERRAL_SKILL_ID, execute_maintenance_deferral)
    return CEPIOApplicationService(
        runtime,
        skill_registry=skills,
        skill_executors=executors,
    )


def recommender_context() -> ExecutionContext:
    return ExecutionContext(
        actor_id="skill-agent-1",
        actor_roles=frozenset({"ai_agent_recommender"}),
        correlation_id="corr-skill-101",
    )


def invocation(*, risk_id: str = "RISK-101", hours: float = 120.0) -> SkillInvocation:
    return SkillInvocation(
        skill_id=MAINTENANCE_DEFERRAL_SKILL_ID,
        subject=ObjectRef(id="P-101", type="Pump"),
        parameters={
            "work_order_id": "WO-101",
            "risk_id": risk_id,
            "proposed_deferral_hours": hours,
        },
        evidence=[
            EvidenceReference(
                object_ref=ObjectRef(id="OBS-101", type="ConditionObservation"),
                role=EvidenceRole.supporting,
                provenance_ref="prov:obs-101",
            ),
            EvidenceReference(
                object_ref=ObjectRef(id="RISK-101", type="Risk"),
                role=EvidenceRole.supporting,
            ),
        ],
        assessment_refs=[ObjectRef(id="RISK-101", type="Risk")],
    )


def test_ready_skill_executes_once_through_contract_and_persists_governed_decision():
    runtime = seed_deferral_case()
    service = application_service(runtime)

    evaluation = service.evaluate_skill(invocation(), recommender_context())

    assert evaluation.status == SkillEvaluationStatus.completed
    assert evaluation.metadata.contract_version == "0.2.0"
    assert evaluation.metadata.correlation_id == "corr-skill-101"
    assert evaluation.outputs["risk_assessment"]["within_supported_window"] is True
    assert evaluation.decision is not None
    assert evaluation.decision.created_by == "skill-agent-1"
    assert evaluation.decision.decision_type == "maintenance-deferral-decision"
    assert evaluation.decision.subject.id == "WO-101"
    assert evaluation.decision.recommended_action == "DeferWorkOrder"
    assert runtime.get_object("WO-101").properties["status"] == "planned"
    assert any("was not executed" in message for message in evaluation.messages)

    evidence_ids = [reference.object_ref.id for reference in evaluation.evidence]
    assert evidence_ids.count("RISK-101") == 1
    assert "OBS-101" in evidence_ids
    assert "WO-101" in evidence_ids
    assert evaluation.evidence[0].provenance_ref == "prov:obs-101"
    assert evaluation.assessment_refs == [ObjectRef(id="RISK-101", type="Risk")]


def test_preflight_blocks_over_authorized_manager_before_executor_runs():
    runtime = seed_deferral_case()
    service = application_service(runtime)
    manager = ExecutionContext(
        actor_id="manager-1",
        actor_roles=frozenset({"maintenance_manager"}),
    )

    evaluation = service.evaluate_skill(invocation(), manager)

    assert evaluation.status == SkillEvaluationStatus.blocked
    assert evaluation.decision is None
    assert any("ACTOR_EXCEEDS_SKILL_AUTHORITY" in message for message in evaluation.messages)
    assert runtime.get_object("WO-101").properties["status"] == "planned"


def test_ready_but_unbound_executable_skill_fails_closed():
    runtime = seed_deferral_case()
    service = application_service(runtime, bind_executor=False)

    evaluation = service.evaluate_skill(invocation(), recommender_context())

    assert evaluation.status == SkillEvaluationStatus.blocked
    assert evaluation.decision is None
    assert any("EXECUTABLE_SKILL_UNBOUND" in message for message in evaluation.messages)


def test_invalid_runtime_evidence_returns_failed_evaluation_without_decision():
    runtime = seed_deferral_case()
    runtime.upsert_object(
        OntologyObject(
            id="RISK-OTHER",
            type="Risk",
            name="Unrelated risk",
            properties={
                "currentRiskScore": 0.1,
                "deferralRiskScore": 0.2,
                "maxSupportedDeferralHours": 720.0,
            },
        )
    )
    service = application_service(runtime)

    evaluation = service.evaluate_skill(
        invocation(risk_id="RISK-OTHER"),
        recommender_context(),
    )

    assert evaluation.status == SkillEvaluationStatus.failed
    assert evaluation.decision is None
    assert any("not linked" in message for message in evaluation.messages)


def test_outside_supported_window_produces_do_not_defer_decision_without_action():
    runtime = seed_deferral_case()
    service = application_service(runtime)

    evaluation = service.evaluate_skill(
        invocation(hours=240.0),
        recommender_context(),
    )

    assert evaluation.status == SkillEvaluationStatus.completed
    assert evaluation.decision is not None
    assert evaluation.decision.recommended_action is None
    assert evaluation.outputs["risk_assessment"]["within_supported_window"] is False
    assert "Do not defer" in (evaluation.recommendation or "")
    assert runtime.get_object("WO-101").properties["status"] == "planned"


def test_application_service_rechecks_function_authority_at_execution_boundary():
    runtime = seed_deferral_case()
    service = CEPIOApplicationService(runtime)
    outsider = ExecutionContext(
        actor_id="outsider-1",
        actor_roles=frozenset({"contract_test_no_access"}),
    )

    with pytest.raises(AuthorizationError, match="not authorized to call function"):
        service.call_function(
            "evaluateMaintenanceDeferralRisk",
            {
                "equipment_id": "P-101",
                "work_order_id": "WO-101",
                "risk_id": "RISK-101",
                "proposed_deferral_hours": 24.0,
            },
            outsider,
        )


def test_executable_registry_rejects_duplicate_skill_binding():
    registry = SkillExecutorRegistry()
    registry.register(MAINTENANCE_DEFERRAL_SKILL_ID, execute_maintenance_deferral)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(MAINTENANCE_DEFERRAL_SKILL_ID, execute_maintenance_deferral)
