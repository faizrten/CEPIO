from datetime import timedelta

import pytest

from cepio import (
    CanonicalPolicyContextProvider,
    PolicyDefinition,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyObligation,
    PolicyObligationKind,
    PolicyRegistry,
    PolicyRule,
    WorkflowPolicyBoundary,
    WorkflowDefinition,
    WorkflowStepDefinition,
    WorkflowStepType,
    WorkflowStatus,
    build_external_kinetic_runtime,
    build_external_resilient_kinetic_runtime,
)
from cepio.bootstrap import build_runtime
from cepio.kinetic import KineticRuntime, SQLiteWorkflowRepository
from cepio.model import ObjectRef, PolicyEffect
from test_kinetic_external import compressor as reference_compressor
from test_kinetic_external import configure_external, register_identity


def compressor():
    target = reference_compressor()
    target.properties["risk_score"] = 0.82
    return target


def policy(version="1.0.0", effect=PolicyEffect.approval_required):
    return PolicyDefinition(
        id="high-risk-maintenance-approval",
        version=version,
        rules=(
            PolicyRule(
                id="high-risk",
                effect=effect,
                conditions=(
                    PolicyCondition(
                        path="context.criticality",
                        operator=PolicyConditionOperator.eq,
                        value="safety_critical",
                    ),
                    PolicyCondition(
                        path="context.risk_score", operator=PolicyConditionOperator.gte, value=0.7
                    ),
                ),
                obligations=(
                    PolicyObligation(
                        kind=PolicyObligationKind.require_approval_authority,
                        parameters={"role": "maintenance_manager"},
                    ),
                    PolicyObligation(kind=PolicyObligationKind.require_evidence),
                    PolicyObligation(kind=PolicyObligationKind.require_decision_record),
                ),
            ),
        ),
        default_effect=PolicyEffect.allow,
    )


def definition(external=False):
    steps = [
        WorkflowStepDefinition(
            id="decision", type=WorkflowStepType.decision, decision_recommendation="Inspect asset"
        ),
        WorkflowStepDefinition(
            id="action",
            type=WorkflowStepType.action,
            operation="CreateInspection",
            parameters={"title": "policy test"},
        ),
    ]
    if external:
        steps.append(
            WorkflowStepDefinition(
                id="verify", type=WorkflowStepType.external_verification, action_step_id="action"
            )
        )
    return WorkflowDefinition(
        id="maintenance", name="Maintenance", steps=steps, policy_references=(policy().reference,)
    )


def start(kinetic):
    return kinetic.start_workflow(
        "maintenance",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="engineer",
        actor_roles={"maintenance_engineer"},
        inputs={"criticality": "low", "approved": True},
    )


@pytest.mark.parametrize("resilient", [False, True])
def test_restart_pins_approval_external_verification_and_outcome(tmp_path, resilient):
    db = tmp_path / "workflow.db"
    runtime = build_runtime(sqlite_path=db)
    runtime.upsert_object(compressor())
    external, adapter = configure_external(runtime, sqlite_path=db)
    register_identity(external)
    factory = (
        build_external_resilient_kinetic_runtime if resilient else build_external_kinetic_runtime
    )
    kinetic = factory(runtime, external, sqlite_path=db)
    kinetic.workflow_policy = WorkflowPolicyBoundary(PolicyRegistry([policy()]))
    if resilient:
        kinetic.register_resilient_workflow(definition(True))
    else:
        kinetic.register_workflow(definition(True))
    paused = start(kinetic)
    assert paused.status == WorkflowStatus.waiting_for_approval
    assert paused.policy_references == (policy().reference,)
    assert adapter.write_calls == []
    task = kinetic.pending_approval(paused.id)
    with pytest.raises(PermissionError):
        kinetic.decide_approval(
            task.id,
            actor_id="agent",
            actor_roles={"ai_agent", "maintenance_engineer"},
            approved=True,
        )
    # Rebuild all runtime boundaries against the durable records, loading both exact versions.
    runtime2 = build_runtime(sqlite_path=db)
    external2, adapter2 = configure_external(runtime2, sqlite_path=db)
    restored = factory(runtime2, external2, sqlite_path=db)
    restored.workflow_policy = WorkflowPolicyBoundary(
        PolicyRegistry([policy(), policy("1.1.0", PolicyEffect.deny)])
    )
    waiting = restored.decide_approval(
        task.id,
        actor_id="manager",
        actor_roles={"maintenance_manager", "maintenance_engineer"},
        approved=True,
    )
    assert waiting.status == WorkflowStatus.waiting_for_external_verification
    assert waiting.policy_references == paused.policy_references
    action_id = waiting.step_states["action"].action_id
    audit = runtime2.audits_for_action(action_id)[0]
    assert audit.policy_evidence["evaluation"]["matched_rules"] == ["high-risk"]
    assert audit.policy_evidence["approval_id"] == task.id
    execution_id = waiting.step_states["verify"].external_execution_id
    assert external2.get_execution(execution_id).policy_evidence == audit.policy_evidence
    restored.tick_external_verification(waiting.id)
    completed = restored.tick_external_verification(waiting.id)
    assert completed.status == WorkflowStatus.completed
    outcome = restored.outcomes(waiting.id)[0]
    assert outcome.evidence["policy_evidence"][0] == audit.policy_evidence
    assert len(adapter2.write_calls) == 1
    restored.tick_external_verification(waiting.id)
    assert len(adapter2.write_calls) == 1
    assert any(h.event == "policy_evaluated" for h in restored.history(waiting.id))


@pytest.mark.parametrize(
    "failure",
    [
        "provider_missing",
        "version_missing",
        "stale",
        "mismatch",
        "missing_context",
        "provider_error",
        "deny",
        "rbac",
    ],
)
def test_policy_fails_closed_without_side_effects(failure):
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    kinetic = KineticRuntime(runtime)

    class Provider(CanonicalPolicyContextProvider):
        def for_action(self, request, target):
            value = super().for_action(request, target)
            if failure == "provider_error":
                raise RuntimeError("trusted service unavailable")
            if failure == "stale":
                return value.model_copy(
                    update={"observed_at": value.observed_at - timedelta(minutes=5)}
                )
            if failure == "mismatch":
                return value.model_copy(update={"subject_version": 999})
            if failure == "missing_context":
                return value.model_copy(update={"context": {}})
            return value

    registry = PolicyRegistry(
        []
        if failure == "version_missing"
        else [policy(effect=PolicyEffect.deny) if failure == "deny" else policy()]
    )
    if failure != "provider_missing":
        kinetic.workflow_policy = WorkflowPolicyBoundary(registry, Provider())
    if failure == "rbac":
        runtime._actions["CreateInspection"].allowed_roles = {"unavailable_role"}
    kinetic.register_workflow(definition())
    result = start(kinetic)
    assert result.status == WorkflowStatus.failed
    assert not any(a.status.value == "executed" for a in runtime.all_audits())


def test_changed_canonical_state_invalidates_approval(tmp_path):
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    kinetic = KineticRuntime(runtime, SQLiteWorkflowRepository(tmp_path / "pins.db"))
    kinetic.workflow_policy = WorkflowPolicyBoundary(PolicyRegistry([policy()]))
    kinetic.register_workflow(definition())
    paused = start(kinetic)
    first = kinetic.pending_approval(paused.id)
    changed = runtime.get_object("K-201")
    changed.properties["risk_score"] = 0.99
    runtime.upsert_object(changed)
    paused_again = kinetic.decide_approval(
        first.id,
        actor_id="human",
        actor_roles={"maintenance_manager", "maintenance_engineer"},
        approved=True,
    )
    assert paused_again.status == WorkflowStatus.waiting_for_approval
    assert kinetic.pending_approval(paused.id).id != first.id
    assert not any(a.status.value == "executed" for a in runtime.all_audits())


@pytest.mark.parametrize(
    "mode",
    [
        "allow",
        "replay_deny",
        "recommend",
        "missing_evidence",
        "missing_decision",
        "no_authority",
        "bad_role",
        "out_of_scope",
    ],
)
def test_obligations_and_policy_before_idempotent_replay(mode):
    from cepio.contextual_policy import PolicyScope
    from cepio.model import ActionRequest
    from cepio.runtime import AuthorizationError

    runtime = build_runtime()
    runtime.upsert_object(compressor())

    class Provider(CanonicalPolicyContextProvider):
        def for_action(self, request, target):
            value = super().for_action(request, target)
            if mode == "missing_evidence":
                return value.model_copy(update={"evidence": {}})
            return value

    base_policy = policy()
    rule = base_policy.rules[0]
    if mode in {"allow", "replay_deny", "missing_decision", "missing_evidence"}:
        rule = rule.model_copy(
            update={
                "effect": PolicyEffect.allow,
                "obligations": tuple(
                    o
                    for o in rule.obligations
                    if o.kind != PolicyObligationKind.require_approval_authority
                ),
            }
        )
    elif mode == "recommend":
        rule = rule.model_copy(update={"effect": PolicyEffect.recommend_only, "obligations": ()})
    elif mode == "no_authority":
        rule = rule.model_copy(update={"obligations": ()})
    elif mode == "bad_role":
        rule = rule.model_copy(
            update={
                "obligations": (
                    PolicyObligation(kind=PolicyObligationKind.require_approval_authority),
                )
            }
        )
    configured = base_policy.model_copy(update={"rules": (rule,)})
    if mode == "out_of_scope":
        configured = configured.model_copy(update={"scope": PolicyScope(actions={"OtherAction"})})
    kinetic = KineticRuntime(runtime)
    registry = PolicyRegistry([configured])
    kinetic.workflow_policy = WorkflowPolicyBoundary(registry, Provider())
    workflow = definition()
    if mode == "missing_decision":
        workflow.steps = workflow.steps[1:]
    kinetic.register_workflow(workflow)
    result = start(kinetic)
    if mode in {"allow", "replay_deny", "out_of_scope"}:
        assert result.status == WorkflowStatus.completed
        step = workflow.steps[-1]
        request = ActionRequest(
            action_type="CreateInspection",
            target=result.subject,
            actor_id="engineer",
            actor_roles={"maintenance_engineer"},
            parameters={"title": "policy test"},
            idempotency_key=f"workflow:{result.id}:step:action",
            workflow_instance_id=result.id,
            decision_id=kinetic._latest_decision_id(result),
        )
        if mode == "replay_deny":
            target = runtime.get_object("K-201")
            target.properties.pop("criticality")
            runtime.upsert_object(target)
            with pytest.raises(AuthorizationError):
                kinetic._execute_workflow_action(result, step, request)
        else:
            replay = kinetic._execute_workflow_action(result, step, request)
            assert replay.replayed
            assert replay.action_id == result.step_states["action"].action_id
            assert (
                replay.policy_evidence["id"]
                != runtime.audits_for_action(replay.action_id)[0].policy_evidence["id"]
            )
    else:
        assert result.status == WorkflowStatus.failed
        assert not any(a.status.value == "executed" for a in runtime.all_audits())


def test_pins_cannot_be_stripped_and_legacy_payload_defaults():
    from pydantic import ValidationError
    from cepio.kinetic import WorkflowInstance

    runtime = build_runtime()
    runtime.upsert_object(compressor())
    kinetic = KineticRuntime(runtime)
    kinetic.workflow_policy = WorkflowPolicyBoundary(PolicyRegistry([policy()]))
    kinetic.register_workflow(definition())
    paused = start(kinetic)
    with pytest.raises(ValidationError):
        paused.policy_references = ()
    tampered = paused.model_copy(update={"policy_references": ()})
    with pytest.raises(PermissionError, match="pins differ"):
        kinetic._execute_workflow_action(tampered, definition().steps[-1], None)
    old_payload = paused.model_dump(mode="json")
    del old_payload["policy_references"]
    assert WorkflowInstance.model_validate(old_payload).policy_references == ()
    with pytest.raises(ValueError):
        WorkflowPolicyBoundary(PolicyRegistry(), max_context_age_seconds=-1)
