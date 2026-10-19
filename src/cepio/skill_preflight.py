from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from .industry_iq import version_satisfies
from .model import ActionRequest, AuditEntry, PolicyEffect
from .registry import AmbiguousTypeError, UnknownTypeError

if TYPE_CHECKING:
    from .runtime import CEPIORuntime


PreflightStatus = Literal["READY", "BLOCKED"]
PreflightCheckStatus = Literal["PASS", "BLOCKED"]


class SkillGraphPathStep(BaseModel):
    """One logical relationship hop required by a Skill procedure."""

    relationship: str
    direction: Literal["out", "in"] = "out"
    target_type: str


class SkillGraphPathRequirement(BaseModel):
    """A semantic path that must be traversable by the Skill actor."""

    id: str
    start_type: str
    steps: list[SkillGraphPathStep] = Field(min_length=1)


class SkillAuthorityContract(BaseModel):
    """Procedure-level authority contract expressed with logical action identifiers."""

    recommend: bool = True
    propose_decision: bool = False
    execute_actions: set[str] = Field(default_factory=set)
    approval_required_for: set[str] = Field(default_factory=set)


class SkillPreflightSpec(BaseModel):
    """Resolved Skill contract evaluated against one concrete CEPIO runtime.

    Semantic bindings use logical identifiers as keys and canonical CEPIO runtime
    identifiers as values. Graph paths remain logical so a package cannot bypass its
    declared binding map when describing evidence traversal. Industry IQ pack IDs are
    deployment capabilities and must be present explicitly when declared by a Skill.
    ``industry_iq_pack_constraints`` adds an optional SemVer compatibility contract;
    legacy ID-only declarations remain equivalent to ``*`` for backward compatibility.
    """

    skill_id: str
    binding_id: str | None = None
    industry_iq_packs: set[str] = Field(default_factory=set)
    industry_iq_pack_constraints: dict[str, str] = Field(default_factory=dict)
    object_types: dict[str, str] = Field(default_factory=dict)
    relationships: dict[str, str] = Field(default_factory=dict)
    functions: dict[str, str] = Field(default_factory=dict)
    decisions: dict[str, str] = Field(default_factory=dict)
    actions: dict[str, str] = Field(default_factory=dict)
    evidence_types: set[str] = Field(default_factory=set)
    graph_paths: list[SkillGraphPathRequirement] = Field(default_factory=list)
    authority: SkillAuthorityContract = Field(default_factory=SkillAuthorityContract)


class SkillPreflightCheck(BaseModel):
    category: str
    logical_id: str | None = None
    runtime_id: str | None = None
    status: PreflightCheckStatus
    code: str
    message: str


class SkillPreflightResult(BaseModel):
    skill_id: str
    binding_id: str | None = None
    actor_id: str
    actor_roles: set[str]
    status: PreflightStatus
    checks: list[SkillPreflightCheck]

    @property
    def blockers(self) -> list[SkillPreflightCheck]:
        return [check for check in self.checks if check.status == "BLOCKED"]


class SkillRegistry:
    """Runtime-local registry for resolved Skill contracts.

    Registration does not imply admission. ``preflight`` re-evaluates the concrete
    runtime and actor every time, so policy or capability changes fail closed.
    """

    def __init__(self, runtime: CEPIORuntime) -> None:
        self.runtime = runtime
        self._skills: dict[str, SkillPreflightSpec] = {}

    def register(self, spec: SkillPreflightSpec) -> None:
        self._skills[spec.skill_id] = spec

    def get(self, skill_id: str) -> SkillPreflightSpec:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"Unknown CEPIO Skill: {skill_id}") from exc

    def preflight(
        self,
        skill_id: str,
        *,
        actor_id: str,
        actor_roles: set[str],
    ) -> SkillPreflightResult:
        return evaluate_skill_preflight(
            self.runtime,
            self.get(skill_id),
            actor_id=actor_id,
            actor_roles=actor_roles,
        )


def evaluate_skill_preflight(
    runtime: CEPIORuntime,
    spec: SkillPreflightSpec,
    *,
    actor_id: str,
    actor_roles: set[str],
) -> SkillPreflightResult:
    """Fail-closed runtime admission for one Skill and actor.

    This is deliberately side-effect free. It verifies deployment capability, runtime
    identity, semantic path validity, evidence visibility, function/decision
    authorization, procedure-aligned action authority and Decision -> Action
    auditability. It does not claim that a particular target instance currently contains
    sufficient evidence; that remains an invocation-time evidence question handled by
    the Operator.
    """

    checks: list[SkillPreflightCheck] = []

    def passed(
        category: str,
        code: str,
        message: str,
        logical_id: str | None = None,
        runtime_id: str | None = None,
    ) -> None:
        checks.append(
            SkillPreflightCheck(
                category=category,
                logical_id=logical_id,
                runtime_id=runtime_id,
                status="PASS",
                code=code,
                message=message,
            )
        )

    def blocked(
        category: str,
        code: str,
        message: str,
        logical_id: str | None = None,
        runtime_id: str | None = None,
    ) -> None:
        checks.append(
            SkillPreflightCheck(
                category=category,
                logical_id=logical_id,
                runtime_id=runtime_id,
                status="BLOCKED",
                code=code,
                message=message,
            )
        )

    installed_packs = runtime.industry_iq_packs
    required_packs = set(spec.industry_iq_packs) | set(spec.industry_iq_pack_constraints)
    for pack_id in sorted(required_packs):
        constraint = spec.industry_iq_pack_constraints.get(pack_id, "*")
        installed_version = installed_packs.get(pack_id)
        if installed_version is None:
            blocked(
                "industry_iq_pack",
                "INDUSTRY_IQ_PACK_UNAVAILABLE",
                "Required Industry IQ pack is not installed in the current runtime.",
                pack_id,
                pack_id,
            )
            continue
        try:
            compatible = version_satisfies(installed_version, constraint)
        except ValueError as exc:
            blocked(
                "industry_iq_pack",
                "INDUSTRY_IQ_PACK_CONSTRAINT_INVALID",
                f"Required Industry IQ pack version constraint is invalid: {exc}",
                pack_id,
                installed_version,
            )
            continue
        if not compatible:
            blocked(
                "industry_iq_pack",
                "INDUSTRY_IQ_PACK_VERSION_INCOMPATIBLE",
                (
                    f"Installed Industry IQ pack version {installed_version} does not satisfy "
                    f"required constraint {constraint}."
                ),
                pack_id,
                installed_version,
            )
        elif constraint in {"", "*"}:
            passed(
                "industry_iq_pack",
                "INDUSTRY_IQ_PACK_AVAILABLE",
                f"Required Industry IQ pack is installed at version {installed_version}.",
                pack_id,
                pack_id,
            )
        else:
            passed(
                "industry_iq_pack",
                "INDUSTRY_IQ_PACK_COMPATIBLE",
                (
                    f"Required Industry IQ pack is installed at version {installed_version} "
                    f"and satisfies constraint {constraint}."
                ),
                pack_id,
                installed_version,
            )

    registry = runtime.type_registry
    if registry is None:
        blocked(
            "runtime",
            "TYPE_REGISTRY_UNAVAILABLE",
            "Runtime type validation is disabled; canonical Skill admission cannot be proven.",
        )
    else:
        for logical_id, runtime_id in sorted(spec.object_types.items()):
            try:
                resolved = registry.resolve_type(runtime_id)
                if resolved != runtime_id:
                    blocked(
                        "object_type",
                        "NON_CANONICAL_RUNTIME_ID",
                        f"Binding resolves to {resolved}; preflight requires canonical object-type identity.",
                        logical_id,
                        runtime_id,
                    )
                else:
                    passed(
                        "object_type",
                        "CANONICAL_TYPE_AVAILABLE",
                        "Canonical object type is registered.",
                        logical_id,
                        runtime_id,
                    )
            except (UnknownTypeError, AmbiguousTypeError) as exc:
                blocked(
                    "object_type",
                    "OBJECT_TYPE_UNAVAILABLE",
                    str(exc),
                    logical_id,
                    runtime_id,
                )

        for logical_id, runtime_id in sorted(spec.relationships.items()):
            try:
                resolved = registry.resolve_relationship(runtime_id)
                if resolved != runtime_id:
                    blocked(
                        "relationship",
                        "NON_CANONICAL_RUNTIME_ID",
                        f"Binding resolves to {resolved}; preflight requires canonical relationship identity.",
                        logical_id,
                        runtime_id,
                    )
                else:
                    passed(
                        "relationship",
                        "CANONICAL_RELATIONSHIP_AVAILABLE",
                        "Canonical relationship is registered.",
                        logical_id,
                        runtime_id,
                    )
            except (UnknownTypeError, AmbiguousTypeError) as exc:
                blocked(
                    "relationship",
                    "RELATIONSHIP_UNAVAILABLE",
                    str(exc),
                    logical_id,
                    runtime_id,
                )

    for logical_id, runtime_id in sorted(spec.functions.items()):
        if not runtime.has_function(runtime_id):
            blocked(
                "function",
                "FUNCTION_UNAVAILABLE",
                "Registered function is unavailable.",
                logical_id,
                runtime_id,
            )
        elif not runtime.policy_engine.can_call_function(actor_roles, runtime_id):
            blocked(
                "function",
                "FUNCTION_NOT_AUTHORIZED",
                "Actor is not authorized to call the required function.",
                logical_id,
                runtime_id,
            )
        else:
            passed(
                "function",
                "FUNCTION_AUTHORIZED",
                "Required function is registered and authorized.",
                logical_id,
                runtime_id,
            )

    for logical_id, runtime_id in sorted(spec.decisions.items()):
        if not runtime.has_decision(runtime_id):
            blocked(
                "decision",
                "DECISION_UNAVAILABLE",
                "Named Decision capability is unavailable.",
                logical_id,
                runtime_id,
            )
        elif not spec.authority.propose_decision:
            blocked(
                "decision",
                "DECISION_AUTHORITY_NOT_DECLARED",
                "Skill depends on a Decision capability but does not declare proposal authority.",
                logical_id,
                runtime_id,
            )
        elif not runtime.policy_engine.can_propose_decision(actor_roles, runtime_id):
            blocked(
                "decision",
                "DECISION_NOT_AUTHORIZED",
                "Actor is not authorized to propose the required Decision.",
                logical_id,
                runtime_id,
            )
        else:
            passed(
                "decision",
                "DECISION_AUTHORIZED",
                "Named Decision is registered and proposal-authorized.",
                logical_id,
                runtime_id,
            )

    if registry is not None:
        for logical_id in sorted(spec.evidence_types):
            runtime_id = spec.object_types.get(logical_id)
            if runtime_id is None:
                blocked(
                    "evidence",
                    "EVIDENCE_TYPE_NOT_BOUND",
                    "Evidence type is not present in the Skill object-type binding map.",
                    logical_id,
                )
                continue
            if not runtime.policy_engine.can_read_type(actor_roles, runtime_id):
                blocked(
                    "evidence",
                    "EVIDENCE_NOT_VISIBLE",
                    "Actor cannot read the required governed evidence type.",
                    logical_id,
                    runtime_id,
                )
            else:
                passed(
                    "evidence",
                    "EVIDENCE_VISIBLE",
                    "Actor can read the required governed evidence type.",
                    logical_id,
                    runtime_id,
                )

        for path in spec.graph_paths:
            current_logical = path.start_type
            current_runtime = spec.object_types.get(current_logical)
            if current_runtime is None:
                blocked(
                    "graph_path",
                    "PATH_START_TYPE_NOT_BOUND",
                    f"Graph path {path.id} starts from an unbound logical type {current_logical}.",
                    path.id,
                )
                continue

            path_ok = True
            for step_index, step in enumerate(path.steps, start=1):
                relationship_runtime = spec.relationships.get(step.relationship)
                target_runtime = spec.object_types.get(step.target_type)
                if relationship_runtime is None or target_runtime is None:
                    missing = (
                        step.relationship if relationship_runtime is None else step.target_type
                    )
                    blocked(
                        "graph_path",
                        "PATH_DEPENDENCY_NOT_BOUND",
                        f"Graph path {path.id} step {step_index} references unbound dependency {missing}.",
                        path.id,
                    )
                    path_ok = False
                    break
                try:
                    if step.direction == "out":
                        registry.validate_relationship_types(
                            relationship_runtime, current_runtime, target_runtime
                        )
                    else:
                        registry.validate_relationship_types(
                            relationship_runtime, target_runtime, current_runtime
                        )
                except (ValueError, UnknownTypeError, AmbiguousTypeError) as exc:
                    blocked(
                        "graph_path",
                        "GRAPH_PATH_INVALID",
                        f"Graph path {path.id} step {step_index} is not semantically traversable: {exc}",
                        path.id,
                        relationship_runtime,
                    )
                    path_ok = False
                    break
                if not runtime.policy_engine.can_read_type(actor_roles, target_runtime):
                    blocked(
                        "graph_path",
                        "GRAPH_PATH_TARGET_NOT_VISIBLE",
                        f"Actor cannot read target type {step.target_type} at path {path.id} step {step_index}.",
                        path.id,
                        target_runtime,
                    )
                    path_ok = False
                    break
                current_logical = step.target_type
                current_runtime = target_runtime
            if path_ok:
                passed(
                    "graph_path",
                    "GRAPH_PATH_REACHABLE",
                    f"Graph path {path.id} is semantically valid and visible to the actor.",
                    path.id,
                )

    action_policy_evaluator = getattr(runtime.policy_engine, "evaluate_action_capability", None)
    action_definitions = getattr(runtime, "_actions", {})
    for logical_id, runtime_id in sorted(spec.actions.items()):
        if not runtime.has_action(runtime_id):
            blocked(
                "action",
                "ACTION_UNAVAILABLE",
                "Governed action is unavailable.",
                logical_id,
                runtime_id,
            )
            continue
        if action_policy_evaluator is None:
            blocked(
                "action",
                "ACTION_PREFLIGHT_UNSUPPORTED",
                "Configured policy engine cannot preflight action capability without executing it.",
                logical_id,
                runtime_id,
            )
            continue

        definition = action_definitions.get(runtime_id)
        if definition is None:
            blocked(
                "action",
                "ACTION_DEFINITION_UNAVAILABLE",
                "Runtime reports the action but does not expose its definition to the preflight engine.",
                logical_id,
                runtime_id,
            )
            continue
        policy = action_policy_evaluator(actor_roles, runtime_id, definition)
        wants_execute = logical_id in spec.authority.execute_actions
        requires_handoff = logical_id in spec.authority.approval_required_for or not wants_execute

        if wants_execute:
            acceptable = {PolicyEffect.allow, PolicyEffect.approval_required}
            if policy.effect not in acceptable:
                blocked(
                    "action",
                    "ACTION_EXECUTION_NOT_AUTHORIZED",
                    f"Skill declares execution authority but runtime policy effect is {policy.effect.value}.",
                    logical_id,
                    runtime_id,
                )
            else:
                passed(
                    "action",
                    "ACTION_EXECUTION_GOVERNED",
                    f"Execution path is governed with policy effect {policy.effect.value}.",
                    logical_id,
                    runtime_id,
                )
        elif spec.authority.recommend and requires_handoff:
            if policy.effect in {PolicyEffect.recommend_only, PolicyEffect.approval_required}:
                passed(
                    "action",
                    "ACTION_HANDOFF_ENFORCED",
                    f"Direct execution is prevented; runtime policy effect is {policy.effect.value}.",
                    logical_id,
                    runtime_id,
                )
            elif policy.effect == PolicyEffect.allow:
                blocked(
                    "action",
                    "ACTOR_EXCEEDS_SKILL_AUTHORITY",
                    "Actor may execute an action that this Skill only declares for recommendation/handoff.",
                    logical_id,
                    runtime_id,
                )
            else:
                blocked(
                    "action",
                    "ACTION_NOT_RECOMMENDABLE",
                    "Actor cannot execute or recommend the action required by the Skill.",
                    logical_id,
                    runtime_id,
                )
        else:
            blocked(
                "action",
                "ACTION_AUTHORITY_CONTRACT_INVALID",
                "Skill declares an action dependency without recommendation or execution authority.",
                logical_id,
                runtime_id,
            )

    if spec.decisions and spec.actions:
        causal_fields_present = (
            "decision_id" in ActionRequest.model_fields
            and "decision_id" in AuditEntry.model_fields
            and hasattr(runtime.audit_repository, "append_audit")
        )
        if causal_fields_present:
            passed(
                "audit",
                "DECISION_ACTION_AUDITABLE",
                "Runtime preserves Decision -> Action causal linkage in governed audit records.",
            )
        else:
            blocked(
                "audit",
                "DECISION_ACTION_AUDIT_UNAVAILABLE",
                "Runtime cannot prove Decision -> Action causal auditability.",
            )

    status: PreflightStatus = (
        "BLOCKED" if any(check.status == "BLOCKED" for check in checks) else "READY"
    )
    return SkillPreflightResult(
        skill_id=spec.skill_id,
        binding_id=spec.binding_id,
        actor_id=actor_id,
        actor_roles=actor_roles,
        status=status,
        checks=checks,
    )