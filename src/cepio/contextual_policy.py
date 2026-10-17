from __future__ import annotations

from enum import Enum
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model import ActionRequest, OntologyObject, PolicyDecision, PolicyEffect
from .policy import ActionDefinitionLike, PolicyEngine


class PolicyConditionOperator(str, Enum):
    eq = "eq"
    neq = "neq"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    contains = "contains"
    in_ = "in"
    not_in = "not_in"
    exists = "exists"


class PolicyObligationKind(str, Enum):
    require_evidence = "require_evidence"
    require_approval_authority = "require_approval_authority"
    require_decision_record = "require_decision_record"


class PolicyReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: str
    version: str


class PolicyScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    actions: frozenset[str] = Field(default_factory=frozenset)
    functions: frozenset[str] = Field(default_factory=frozenset)
    resource_types: frozenset[str] = Field(default_factory=frozenset)

    @staticmethod
    def _matches(value: str | None, allowed: frozenset[str]) -> bool:
        if not allowed:
            return True
        if value is None:
            return False
        return "*" in allowed or value in allowed

    def matches(self, context: "PolicyEvaluationContext") -> bool:
        return (
            self._matches(context.action_type, self.actions)
            and self._matches(context.function_name, self.functions)
            and self._matches(context.subject_type, self.resource_types)
        )


class PolicyCondition(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    operator: PolicyConditionOperator
    value: Any = None

    @model_validator(mode="after")
    def validate_value(self) -> "PolicyCondition":
        if not self.path.strip():
            raise ValueError("Policy condition path must not be empty")
        if self.operator != PolicyConditionOperator.exists and self.value is None:
            raise ValueError(f"Policy condition {self.path!r} requires a comparison value")
        return self


class PolicyObligation(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: PolicyObligationKind
    parameters: dict[str, Any] = Field(default_factory=dict)


class PolicyRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    effect: PolicyEffect
    conditions: tuple[PolicyCondition, ...] = ()
    obligations: tuple[PolicyObligation, ...] = ()
    reason: str | None = None
    priority: int = 0


class PolicyDefinition(BaseModel):
    """Immutable, version-addressable contextual policy contract."""

    model_config = ConfigDict(frozen=True)

    id: str
    version: str
    description: str | None = None
    scope: PolicyScope = Field(default_factory=PolicyScope)
    rules: tuple[PolicyRule, ...]
    default_effect: PolicyEffect = PolicyEffect.deny
    default_reason: str = "No contextual policy rule matched"

    @model_validator(mode="after")
    def validate_definition(self) -> "PolicyDefinition":
        if not self.id.strip() or not self.version.strip():
            raise ValueError("Policy id and version must not be empty")
        rule_ids = [rule.id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError(f"Policy {self.id}@{self.version} contains duplicate rule ids")
        return self

    @property
    def reference(self) -> PolicyReference:
        return PolicyReference(policy_id=self.id, version=self.version)


class PolicyEvaluationContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    actor_id: str | None = None
    actor_roles: frozenset[str] = Field(default_factory=frozenset)
    action_type: str | None = None
    function_name: str | None = None
    subject_id: str | None = None
    subject_type: str | None = None
    subject_properties: dict[str, Any] = Field(default_factory=dict)
    action_parameters: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def for_action(
        cls,
        request: ActionRequest,
        target: OntologyObject,
        *,
        context: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> "PolicyEvaluationContext":
        return cls(
            actor_id=request.actor_id,
            actor_roles=frozenset(request.actor_roles),
            action_type=request.action_type,
            subject_id=target.id,
            subject_type=target.type,
            subject_properties=dict(target.properties),
            action_parameters=dict(request.parameters),
            context=context or {},
            evidence=evidence or {},
        )

    def as_document(self) -> dict[str, Any]:
        return {
            "actor": {"id": self.actor_id, "roles": self.actor_roles},
            "action": {"type": self.action_type, "parameters": self.action_parameters},
            "function": {"name": self.function_name},
            "subject": {
                "id": self.subject_id,
                "type": self.subject_type,
                "properties": self.subject_properties,
            },
            "context": self.context,
            "evidence": self.evidence,
        }


class PolicyConditionEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    operator: PolicyConditionOperator
    expected: Any = None
    actual: Any = None
    matched: bool = False
    indeterminate: bool = False
    reason: str | None = None


class PolicyRuleEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: PolicyReference
    rule_id: str
    matched: bool
    effect: PolicyEffect | None = None
    conditions: tuple[PolicyConditionEvaluation, ...] = ()
    reason: str | None = None


class PolicyEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    effect: PolicyEffect
    reasons: tuple[str, ...] = ()
    obligations: tuple[PolicyObligation, ...] = ()
    evaluated_policies: tuple[PolicyReference, ...] = ()
    matched_rules: tuple[str, ...] = ()
    rule_evaluations: tuple[PolicyRuleEvaluation, ...] = ()
    indeterminate: bool = False

    def to_policy_decision(self) -> PolicyDecision:
        return PolicyDecision(
            effect=self.effect,
            reasons=list(self.reasons),
            requires_human_approval=self.effect == PolicyEffect.approval_required,
        )


class PolicyRegistry:
    """In-memory immutable-version registry keyed by (policy id, version)."""

    def __init__(self, definitions: Iterable[PolicyDefinition] = ()) -> None:
        self._definitions: dict[tuple[str, str], PolicyDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: PolicyDefinition) -> PolicyDefinition:
        key = (definition.id, definition.version)
        existing = self._definitions.get(key)
        if existing is not None:
            if existing != definition:
                raise ValueError(f"Policy version {definition.id}@{definition.version} is immutable")
            return existing
        self._definitions[key] = definition
        return definition

    def resolve(self, policy_id: str, version: str) -> PolicyDefinition:
        try:
            return self._definitions[(policy_id, version)]
        except KeyError as exc:
            raise KeyError(f"Unknown policy version {policy_id}@{version}") from exc

    def resolve_reference(self, reference: PolicyReference) -> PolicyDefinition:
        return self.resolve(reference.policy_id, reference.version)


_MISSING = object()
_EFFECT_PRECEDENCE = {
    PolicyEffect.allow: 0,
    PolicyEffect.recommend_only: 1,
    PolicyEffect.approval_required: 2,
    PolicyEffect.deny: 3,
}


def _resolve_path(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return _MISSING
    return current


def _condition_result(condition: PolicyCondition, document: dict[str, Any]) -> PolicyConditionEvaluation:
    actual = _resolve_path(document, condition.path)
    if condition.operator == PolicyConditionOperator.exists:
        expected = True if condition.value is None else bool(condition.value)
        matched = (actual is not _MISSING) == expected
        return PolicyConditionEvaluation(
            path=condition.path,
            operator=condition.operator,
            expected=expected,
            actual=None if actual is _MISSING else actual,
            matched=matched,
        )

    if actual is _MISSING:
        return PolicyConditionEvaluation(
            path=condition.path,
            operator=condition.operator,
            expected=condition.value,
            indeterminate=True,
            reason="Required contextual value is missing",
        )

    try:
        op = condition.operator
        expected = condition.value
        if op == PolicyConditionOperator.eq:
            matched = actual == expected
        elif op == PolicyConditionOperator.neq:
            matched = actual != expected
        elif op == PolicyConditionOperator.gt:
            matched = actual > expected
        elif op == PolicyConditionOperator.gte:
            matched = actual >= expected
        elif op == PolicyConditionOperator.lt:
            matched = actual < expected
        elif op == PolicyConditionOperator.lte:
            matched = actual <= expected
        elif op == PolicyConditionOperator.contains:
            matched = expected in actual
        elif op == PolicyConditionOperator.in_:
            matched = actual in expected
        elif op == PolicyConditionOperator.not_in:
            matched = actual not in expected
        else:  # pragma: no cover - enum validation makes this defensive only
            raise ValueError(f"Unsupported policy operator {op}")
        return PolicyConditionEvaluation(
            path=condition.path,
            operator=condition.operator,
            expected=expected,
            actual=actual,
            matched=matched,
        )
    except (TypeError, ValueError) as exc:
        return PolicyConditionEvaluation(
            path=condition.path,
            operator=condition.operator,
            expected=condition.value,
            actual=actual,
            indeterminate=True,
            reason=f"Condition could not be evaluated: {exc}",
        )


def evaluate_policy_definition(
    definition: PolicyDefinition, context: PolicyEvaluationContext
) -> PolicyEvaluation | None:
    """Evaluate one exact policy version. Returns None when the policy is out of scope."""

    if not definition.scope.matches(context):
        return None

    document = context.as_document()
    rule_evaluations: list[PolicyRuleEvaluation] = []
    matched: list[PolicyRule] = []
    indeterminate_reasons: list[str] = []

    for rule in sorted(definition.rules, key=lambda item: item.priority, reverse=True):
        condition_results = tuple(_condition_result(condition, document) for condition in rule.conditions)
        indeterminate = [result for result in condition_results if result.indeterminate]
        if indeterminate:
            for result in indeterminate:
                indeterminate_reasons.append(
                    f"{definition.id}@{definition.version}/{rule.id}: {result.path}: {result.reason}"
                )
            rule_evaluations.append(
                PolicyRuleEvaluation(
                    policy=definition.reference,
                    rule_id=rule.id,
                    matched=False,
                    conditions=condition_results,
                    reason="Rule evaluation was indeterminate",
                )
            )
            continue

        is_match = all(result.matched for result in condition_results)
        if is_match:
            matched.append(rule)
        rule_evaluations.append(
            PolicyRuleEvaluation(
                policy=definition.reference,
                rule_id=rule.id,
                matched=is_match,
                effect=rule.effect if is_match else None,
                conditions=condition_results,
                reason=rule.reason,
            )
        )

    if indeterminate_reasons:
        return PolicyEvaluation(
            effect=PolicyEffect.deny,
            reasons=tuple(["Contextual policy evaluation failed closed", *indeterminate_reasons]),
            evaluated_policies=(definition.reference,),
            rule_evaluations=tuple(rule_evaluations),
            indeterminate=True,
        )

    if not matched:
        return PolicyEvaluation(
            effect=definition.default_effect,
            reasons=(definition.default_reason,),
            evaluated_policies=(definition.reference,),
            rule_evaluations=tuple(rule_evaluations),
        )

    effect = max((rule.effect for rule in matched), key=lambda item: _EFFECT_PRECEDENCE[item])
    reasons = tuple(rule.reason or f"Matched rule {rule.id}" for rule in matched)
    obligations = tuple(obligation for rule in matched for obligation in rule.obligations)
    return PolicyEvaluation(
        effect=effect,
        reasons=reasons,
        obligations=obligations,
        evaluated_policies=(definition.reference,),
        matched_rules=tuple(rule.id for rule in matched),
        rule_evaluations=tuple(rule_evaluations),
    )


def evaluate_policy_set(
    registry: PolicyRegistry,
    references: Iterable[PolicyReference],
    context: PolicyEvaluationContext,
) -> PolicyEvaluation | None:
    evaluations = [
        evaluation
        for reference in references
        if (evaluation := evaluate_policy_definition(registry.resolve_reference(reference), context)) is not None
    ]
    if not evaluations:
        return None

    effect = max((evaluation.effect for evaluation in evaluations), key=lambda item: _EFFECT_PRECEDENCE[item])
    return PolicyEvaluation(
        effect=effect,
        reasons=tuple(reason for evaluation in evaluations for reason in evaluation.reasons),
        obligations=tuple(obligation for evaluation in evaluations for obligation in evaluation.obligations),
        evaluated_policies=tuple(reference for evaluation in evaluations for reference in evaluation.evaluated_policies),
        matched_rules=tuple(rule for evaluation in evaluations for rule in evaluation.matched_rules),
        rule_evaluations=tuple(item for evaluation in evaluations for item in evaluation.rule_evaluations),
        indeterminate=any(evaluation.indeterminate for evaluation in evaluations),
    )


def _combine_decisions(legacy: PolicyDecision, contextual: PolicyEvaluation | None) -> PolicyDecision:
    if contextual is None:
        return legacy
    effect = max((legacy.effect, contextual.effect), key=lambda item: _EFFECT_PRECEDENCE[item])
    return PolicyDecision(
        effect=effect,
        reasons=[*legacy.reasons, *contextual.reasons],
        allowed_properties=legacy.allowed_properties,
        requires_human_approval=(
            legacy.requires_human_approval or effect == PolicyEffect.approval_required
        ),
    )


class ContextualPolicyEngine:
    """Add contextual policy without weakening the existing policy engine.

    Runtime action decisions are deny-dominant across the legacy engine and exact,
    version-pinned contextual policies. Read, function and decision-proposal policy
    remain delegated to the existing engine in this first migration slice.
    """

    def __init__(
        self,
        *,
        legacy: PolicyEngine,
        registry: PolicyRegistry,
        policy_references: Iterable[PolicyReference] = (),
    ) -> None:
        self.legacy = legacy
        self.registry = registry
        self.policy_references = tuple(policy_references)

    def evaluate_action(
        self, request: ActionRequest, target: OntologyObject, definition: ActionDefinitionLike
    ) -> PolicyDecision:
        legacy_decision = self.legacy.evaluate_action(request, target, definition)
        contextual = evaluate_policy_set(
            self.registry,
            self.policy_references,
            PolicyEvaluationContext.for_action(request, target),
        )
        return _combine_decisions(legacy_decision, contextual)

    def evaluate_action_with_context(
        self,
        request: ActionRequest,
        target: OntologyObject,
        definition: ActionDefinitionLike,
        *,
        context: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> tuple[PolicyDecision, PolicyEvaluation | None]:
        legacy_decision = self.legacy.evaluate_action(request, target, definition)
        contextual = evaluate_policy_set(
            self.registry,
            self.policy_references,
            PolicyEvaluationContext.for_action(request, target, context=context, evidence=evidence),
        )
        return _combine_decisions(legacy_decision, contextual), contextual

    def evaluate_action_capability(
        self, roles: set[str], action_type: str, definition: ActionDefinitionLike
    ) -> PolicyDecision:
        # Capability preflight proves base authority only. Instance-specific contextual
        # policy is evaluated again at runtime when subject/risk/evidence are available.
        return self.legacy.evaluate_action_capability(roles, action_type, definition)

    def can_read_type(self, roles: set[str], object_type: str) -> bool:
        return self.legacy.can_read_type(roles, object_type)

    def can_read_object(self, roles: set[str], obj: OntologyObject) -> bool:
        return self.legacy.can_read_object(roles, obj)

    def filter_properties(self, roles: set[str], obj: OntologyObject) -> OntologyObject:
        return self.legacy.filter_properties(roles, obj)

    def can_call_function(self, roles: set[str], function_name: str) -> bool:
        return self.legacy.can_call_function(roles, function_name)

    def can_propose_decision(self, roles: set[str], decision_type: str) -> bool:
        return self.legacy.can_propose_decision(roles, decision_type)
