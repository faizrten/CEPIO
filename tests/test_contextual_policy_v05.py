from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cepio.contextual_policy import (
    ContextualPolicyEngine,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyDefinition,
    PolicyEvaluationContext,
    PolicyObligation,
    PolicyObligationKind,
    PolicyReference,
    PolicyRegistry,
    PolicyRule,
    PolicyScope,
    evaluate_policy_definition,
)
from cepio.model import ActionRequest, ObjectRef, OntologyObject, PolicyEffect
from cepio.policy import RolePolicyEngine


@dataclass
class ActionDefinitionStub:
    name: str = "CreateWorkOrder"
    allowed_roles: set[str] = field(default_factory=lambda: {"maintenance_engineer"})
    requires_human_approval: bool = False


def compressor(criticality: str = "high") -> OntologyObject:
    return OntologyObject(
        id="K-201",
        type="Compressor",
        name="Recycle Gas Compressor K-201",
        properties={"criticality": criticality, "operatingState": "degraded"},
    )


def request(*, roles: set[str] | None = None, risk_score: float | None = 0.82) -> ActionRequest:
    parameters = {} if risk_score is None else {"risk_score": risk_score}
    return ActionRequest(
        action_type="CreateWorkOrder",
        target=ObjectRef(id="K-201", type="Compressor"),
        actor_id="m1",
        actor_roles=roles or {"maintenance_engineer"},
        parameters=parameters,
    )


def high_risk_policy(version: str = "1.0.0") -> PolicyDefinition:
    return PolicyDefinition(
        id="high-risk-maintenance-approval",
        version=version,
        description="Require approval and evidence for high-risk maintenance execution.",
        scope=PolicyScope(
            actions={"CreateWorkOrder"},
            resource_types={"Compressor"},
        ),
        rules=(
            PolicyRule(
                id="high-criticality-high-risk",
                priority=100,
                effect=PolicyEffect.approval_required,
                conditions=(
                    PolicyCondition(
                        path="subject.properties.criticality",
                        operator=PolicyConditionOperator.in_,
                        value=["high", "safety_critical"],
                    ),
                    PolicyCondition(
                        path="action.parameters.risk_score",
                        operator=PolicyConditionOperator.gte,
                        value=0.7,
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
                reason="High-criticality maintenance above the risk threshold requires approval",
            ),
        ),
        default_effect=PolicyEffect.allow,
        default_reason="High-risk approval rule not triggered",
    )


def test_policy_versions_are_immutable_and_resolved_exactly():
    v1 = high_risk_policy("1.0.0")
    v2 = high_risk_policy("1.1.0")
    registry = PolicyRegistry([v1, v2])

    assert registry.resolve("high-risk-maintenance-approval", "1.0.0") == v1
    assert registry.resolve_reference(PolicyReference(policy_id=v2.id, version=v2.version)) == v2

    changed_v1 = v1.model_copy(update={"default_effect": PolicyEffect.deny})
    with pytest.raises(ValueError, match="immutable"):
        registry.register(changed_v1)

    with pytest.raises(KeyError, match="Unknown policy version"):
        registry.resolve(v1.id, "2.0.0")


def test_high_risk_rule_requires_approval_and_emits_obligations():
    definition = high_risk_policy()
    evaluation = evaluate_policy_definition(
        definition,
        PolicyEvaluationContext.for_action(request(), compressor()),
    )

    assert evaluation is not None
    assert evaluation.effect == PolicyEffect.approval_required
    assert evaluation.matched_rules == ("high-criticality-high-risk",)
    assert {item.kind for item in evaluation.obligations} == {
        PolicyObligationKind.require_approval_authority,
        PolicyObligationKind.require_evidence,
        PolicyObligationKind.require_decision_record,
    }
    assert evaluation.indeterminate is False


def test_missing_governed_context_fails_closed():
    definition = high_risk_policy()
    evaluation = evaluate_policy_definition(
        definition,
        PolicyEvaluationContext.for_action(request(risk_score=None), compressor()),
    )

    assert evaluation is not None
    assert evaluation.effect == PolicyEffect.deny
    assert evaluation.indeterminate is True
    assert any("risk_score" in reason for reason in evaluation.reasons)


def test_non_high_risk_case_uses_explicit_policy_default():
    evaluation = evaluate_policy_definition(
        high_risk_policy(),
        PolicyEvaluationContext.for_action(request(risk_score=0.4), compressor("medium")),
    )

    assert evaluation is not None
    assert evaluation.effect == PolicyEffect.allow
    assert evaluation.matched_rules == ()


def test_policy_out_of_scope_does_not_affect_action():
    evaluation = evaluate_policy_definition(
        high_risk_policy(),
        PolicyEvaluationContext(
            actor_id="m1",
            actor_roles={"maintenance_engineer"},
            action_type="CreateInspection",
            subject_id="K-201",
            subject_type="Compressor",
        ),
    )
    assert evaluation is None


def test_contextual_engine_never_loosens_legacy_rbac():
    registry = PolicyRegistry([high_risk_policy()])
    legacy = RolePolicyEngine()
    engine = ContextualPolicyEngine(
        legacy=legacy,
        registry=registry,
        policy_references=[high_risk_policy().reference],
    )

    denied = engine.evaluate_action(
        request(roles={"ai_agent_recommender"}, risk_score=0.4),
        compressor("medium"),
        ActionDefinitionStub(),
    )
    assert denied.effect == PolicyEffect.deny


def test_contextual_engine_can_raise_legacy_allow_to_approval_required():
    definition = high_risk_policy()
    engine = ContextualPolicyEngine(
        legacy=RolePolicyEngine(),
        registry=PolicyRegistry([definition]),
        policy_references=[definition.reference],
    )

    decision = engine.evaluate_action(request(), compressor(), ActionDefinitionStub())
    assert decision.effect == PolicyEffect.approval_required
    assert decision.requires_human_approval is True
    assert any("risk threshold" in reason for reason in decision.reasons)


def test_capability_preflight_remains_base_authority_check():
    definition = high_risk_policy()
    engine = ContextualPolicyEngine(
        legacy=RolePolicyEngine(),
        registry=PolicyRegistry([definition]),
        policy_references=[definition.reference],
    )

    decision = engine.evaluate_action_capability(
        {"maintenance_engineer"}, "CreateWorkOrder", ActionDefinitionStub()
    )
    assert decision.effect == PolicyEffect.allow
