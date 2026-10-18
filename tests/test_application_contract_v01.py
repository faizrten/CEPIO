from __future__ import annotations

from dataclasses import dataclass

import pytest

from cepio.application_contract import (
    APPLICATION_CONTRACT_VERSION,
    ActionIntent,
    CEPIOApplicationService,
    ContextEnvelope,
    DecisionProposal,
    EvidenceReference,
    EvidenceRole,
    ExecutionContext,
    SkillEvaluation,
    SkillEvaluationStatus,
    SkillInvocation,
)
from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject
from cepio.runtime import AuthorizationError


@dataclass(frozen=True)
class Principal:
    actor_id: str
    roles: set[str]
    tenant_id: str | None = None


def seed_work_order_runtime():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="WO-101",
            type="WorkOrder",
            name="Seal replacement",
            properties={"status": "planned", "priority": "high"},
        )
    )
    return runtime


def test_contract_payloads_are_protocol_neutral_and_identity_free():
    action_fields = ActionIntent.model_fields
    decision_fields = DecisionProposal.model_fields
    skill_fields = SkillInvocation.model_fields

    assert "actor_id" not in action_fields
    assert "actor_roles" not in action_fields
    assert "created_by" not in decision_fields
    assert "actor_id" not in skill_fields
    assert APPLICATION_CONTRACT_VERSION == "0.1.0"


def test_execution_context_is_derived_from_trusted_principal():
    principal = Principal(
        actor_id="manager-1",
        roles={"maintenance_manager"},
        tenant_id="tenant-a",
    )
    context = ExecutionContext.from_principal(principal, correlation_id="corr-1")

    assert context.actor_id == "manager-1"
    assert context.actor_roles == frozenset({"maintenance_manager"})
    assert context.tenant_id == "tenant-a"
    assert context.correlation_id == "corr-1"


def test_decision_and_action_use_same_contract_service_with_host_injected_identity():
    runtime = seed_work_order_runtime()
    service = CEPIOApplicationService(runtime)
    manager = ExecutionContext(
        actor_id="manager-1",
        actor_roles=frozenset({"maintenance_manager"}),
        correlation_id="corr-123",
    )

    decision = service.propose_decision(
        DecisionProposal(
            decision_type="maintenance-deferral-decision",
            subject=ObjectRef(id="WO-101", type="WorkOrder"),
            problem="Can this work order be deferred to the planned outage?",
            recommendation="Defer within the governed maintenance window.",
            recommended_action="DeferWorkOrder",
            confidence=0.82,
        ),
        manager,
    )
    assert decision.created_by == "manager-1"

    result = service.execute_action(
        ActionIntent(
            action_type="DeferWorkOrder",
            target=ObjectRef(id="WO-101", type="WorkOrder"),
            parameters={"reason": "planned outage", "until": "2026-11-01"},
            decision_id=decision.id,
        ),
        manager,
    )

    assert result.status.value == "executed"
    audits = runtime.audits_for_action(result.action_id)
    assert audits[-1].actor_id == "manager-1"
    assert audits[-1].decision_id == decision.id
    assert audits[-1].correlation_id == "corr-123"


def test_application_service_preserves_runtime_decision_authorization():
    runtime = seed_work_order_runtime()
    service = CEPIOApplicationService(runtime)
    auditor = ExecutionContext(actor_id="audit-1", actor_roles=frozenset({"auditor"}))

    with pytest.raises(AuthorizationError, match="not authorized to propose"):
        service.propose_decision(
            DecisionProposal(
                decision_type="maintenance-deferral-decision",
                subject=ObjectRef(id="WO-101", type="WorkOrder"),
                problem="Unauthorized decision",
                recommendation="Do not persist",
            ),
            auditor,
        )


def test_application_service_delegates_object_visibility_to_runtime():
    runtime = seed_work_order_runtime()
    service = CEPIOApplicationService(runtime)
    manager = ExecutionContext(
        actor_id="manager-1",
        actor_roles=frozenset({"maintenance_manager"}),
    )
    auditor = ExecutionContext(actor_id="audit-1", actor_roles=frozenset({"auditor"}))

    visible = service.read_object("WO-101", manager)
    assert visible.id == "WO-101"

    with pytest.raises(AuthorizationError, match="not authorized to read object type WorkOrder"):
        service.read_object("WO-101", auditor)


def test_skill_preflight_fails_closed_without_registry():
    service = CEPIOApplicationService(seed_work_order_runtime())
    manager = ExecutionContext(
        actor_id="manager-1",
        actor_roles=frozenset({"maintenance_manager"}),
    )

    with pytest.raises(RuntimeError, match="no SkillRegistry configured"):
        service.preflight_skill(
            "cepio.skill.maintenance.assess-maintenance-deferral",
            manager,
        )


def test_context_and_skill_envelopes_reference_governed_objects_without_transport_semantics():
    subject = OntologyObject(id="P-101", type="Pump", name="P-101")
    evidence = EvidenceReference(
        object_ref=ObjectRef(id="OBS-101", type="ConditionObservation"),
        role=EvidenceRole.supporting,
        provenance_ref="prov:obs-101",
    )
    context = ContextEnvelope(subject=subject, evidence=[evidence])
    invocation = SkillInvocation(
        skill_id="cepio.skill.maintenance.assess-maintenance-deferral",
        subject=ObjectRef(id="P-101", type="Pump"),
        evidence=[evidence],
    )
    evaluation = SkillEvaluation(
        skill_id=invocation.skill_id,
        subject=invocation.subject,
        status=SkillEvaluationStatus.completed,
        recommendation="Inspect before extending the deferral window.",
        evidence=invocation.evidence,
    )

    assert context.metadata.contract_version == "0.1.0"
    assert evaluation.metadata.contract_version == "0.1.0"
    assert evaluation.evidence[0].object_ref.id == "OBS-101"

    serialized = evaluation.model_dump(mode="json")
    rendered = str(serialized).lower()
    assert "http" not in rendered
    assert "mcp" not in rendered
