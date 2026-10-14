from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, TypeAdapter

from .model import (
    ActionRequest,
    ActionResult,
    ActionStatus,
    AuditEntry,
    Decision,
    OntologyObject,
    OperationalEvent,
    PolicyDecision,
    PolicyEffect,
    Relationship,
)
from .policy import PolicyEngine, RolePolicyEngine
from .registry import TypeRegistry
from .repositories import (
    AuditRepository,
    DecisionRepository,
    EventRepository,
    InMemoryRepository,
    ObjectRepository,
)

ActionHandler = Callable[[ActionRequest, OntologyObject, "CEPIORuntime"], dict[str, Any]]
Precondition = Callable[[ActionRequest, OntologyObject, "CEPIORuntime"], tuple[bool, str]]
CompensationHandler = Callable[[ActionRequest, OntologyObject, dict[str, Any], "CEPIORuntime"], dict[str, Any]]
FunctionHandler = Callable[..., Any]


class AuthorizationError(PermissionError):
    def __init__(self, message: str, result: ActionResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class PreconditionsError(RuntimeError):
    pass


@dataclass
class ActionDefinition:
    name: str
    handler: ActionHandler
    allowed_roles: set[str] = field(default_factory=set)
    preconditions: list[Precondition] = field(default_factory=list)
    requires_human_approval: bool = False
    compensation_handler: CompensationHandler | None = None
    compensation_description: str | None = None


@dataclass
class FunctionDefinition:
    name: str
    handler: FunctionHandler
    input_model: type[BaseModel] | None = None
    output_type: Any | None = None


class CEPIORuntime:
    """Vendor-neutral operational ontology runtime."""

    def __init__(
        self,
        object_repository: ObjectRepository | None = None,
        event_repository: EventRepository | None = None,
        audit_repository: AuditRepository | None = None,
        decision_repository: DecisionRepository | None = None,
        policy_engine: PolicyEngine | None = None,
        type_registry: TypeRegistry | None = None,
    ) -> None:
        shared = InMemoryRepository()
        self.object_repository = object_repository or shared
        self.event_repository = event_repository or shared
        self.audit_repository = audit_repository or shared
        self.decision_repository = decision_repository or shared
        self.policy_engine = policy_engine or RolePolicyEngine()
        self.type_registry = type_registry
        self._actions: dict[str, ActionDefinition] = {}
        self._functions: dict[str, FunctionDefinition] = {}

    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject:
        if self.type_registry and not self.type_registry.is_declared_type(obj.type):
            raise ValueError(f"Undeclared CEPIO object type: {obj.type}")
        return self.object_repository.upsert_object(obj, expected_version=expected_version)

    def get_object(self, object_id: str) -> OntologyObject:
        obj = self.object_repository.get_object(object_id)
        if not obj:
            raise KeyError(f"Unknown CEPIO object: {object_id}")
        return obj

    def list_objects(self, object_type: str | None = None) -> list[OntologyObject]:
        return self.object_repository.list_objects(object_type)

    def add_relationship(self, rel: Relationship) -> Relationship:
        source = self.get_object(rel.source.id)
        target = self.get_object(rel.target.id)
        if source.type != rel.source.type:
            raise ValueError(f"Relationship source ref type mismatch for {source.id}")
        if target.type != rel.target.type:
            raise ValueError(f"Relationship target ref type mismatch for {target.id}")
        if self.type_registry:
            if not self.type_registry.is_declared_relationship(rel.type):
                raise ValueError(f"Undeclared CEPIO relationship type: {rel.type}")
            self.type_registry.validate_relationship_types(rel.type, source.type, target.type)
        return self.object_repository.add_relationship(rel)

    def neighbors(self, object_id: str, relationship_type: str | None = None) -> list[OntologyObject]:
        self.get_object(object_id)
        result: list[OntologyObject] = []
        for rel in self.object_repository.get_relationships(object_id, direction="out"):
            if relationship_type is None or rel.type == relationship_type:
                result.append(self.get_object(rel.target.id))
        return result

    def reverse_neighbors(self, object_id: str, relationship_type: str | None = None) -> list[OntologyObject]:
        self.get_object(object_id)
        result: list[OntologyObject] = []
        for rel in self.object_repository.get_relationships(object_id, direction="in"):
            if relationship_type is None or rel.type == relationship_type:
                result.append(self.get_object(rel.source.id))
        return result

    def traverse(self, start_id: str, path: list[str]) -> list[OntologyObject]:
        current = [self.get_object(start_id)]
        for step in path:
            inverse = step.startswith("^")
            relationship_type = step[1:] if inverse else step
            next_objects: dict[str, OntologyObject] = {}
            for obj in current:
                neighbors = self.reverse_neighbors(obj.id, relationship_type) if inverse else self.neighbors(obj.id, relationship_type)
                for neighbor in neighbors:
                    next_objects[neighbor.id] = neighbor
            current = list(next_objects.values())
        return current

    def record_event(self, event: OperationalEvent) -> OperationalEvent:
        self.get_object(event.subject.id)
        return self.event_repository.append_event(event)

    def events_for(self, object_id: str) -> list[OperationalEvent]:
        self.get_object(object_id)
        return self.event_repository.events_for(object_id)

    def register_action(
        self,
        name: str,
        handler: ActionHandler,
        allowed_roles: set[str],
        *,
        preconditions: list[Precondition] | None = None,
        requires_human_approval: bool = False,
        compensation_handler: CompensationHandler | None = None,
        compensation_description: str | None = None,
    ) -> None:
        self._actions[name] = ActionDefinition(
            name=name,
            handler=handler,
            allowed_roles=allowed_roles,
            preconditions=preconditions or [],
            requires_human_approval=requires_human_approval,
            compensation_handler=compensation_handler,
            compensation_description=compensation_description,
        )

    def execute_action(self, request: ActionRequest) -> ActionResult:
        try:
            target = self.get_object(request.target.id)
        except KeyError as exc:
            result = ActionResult(action_type=request.action_type, target=request.target, status=ActionStatus.failed, message=str(exc))
            audit = self._audit(request, result, None)
            result.audit_id = audit.id
            return result

        definition = self._actions.get(request.action_type)
        if not definition:
            result = ActionResult(action_type=request.action_type, target=request.target, status=ActionStatus.failed, message="Unknown action type")
            audit = self._audit(request, result, None)
            result.audit_id = audit.id
            return result

        policy = self.policy_engine.evaluate_action(request, target, definition)
        if policy.effect != PolicyEffect.allow:
            result = ActionResult(
                action_type=request.action_type,
                target=request.target,
                status=ActionStatus.rejected,
                message="; ".join(policy.reasons) or "Action rejected by policy",
                policy_reasons=policy.reasons,
            )
            audit = self._audit(request, result, policy)
            result.audit_id = audit.id
            raise AuthorizationError(result.message, result=result)

        scoped_key = self._scoped_idempotency_key(request)
        if scoped_key:
            prior = self.audit_repository.get_idempotent_result(scoped_key)
            if prior:
                replay = prior.model_copy(deep=True)
                replay.replayed = True
                audit = self._audit(request, replay, policy, replayed=True)
                replay.audit_id = audit.id
                return replay

        failed_preconditions = []
        for check in definition.preconditions:
            ok, reason = check(request, target, self)
            if not ok:
                failed_preconditions.append(reason)
        if failed_preconditions:
            result = ActionResult(
                action_type=request.action_type,
                target=request.target,
                status=ActionStatus.rejected,
                message="Preconditions failed: " + "; ".join(failed_preconditions),
                policy_reasons=policy.reasons,
            )
            audit = self._audit(request, result, policy)
            result.audit_id = audit.id
            self._cache_idempotent(scoped_key, result)
            return result

        try:
            effects = definition.handler(request, target, self)
            result = ActionResult(
                action_type=request.action_type,
                target=request.target,
                status=ActionStatus.executed,
                message="Action executed",
                effects=effects,
                policy_reasons=policy.reasons,
                compensation=(
                    {"available": True, "description": definition.compensation_description}
                    if definition.compensation_handler
                    else None
                ),
            )
        except Exception as exc:
            result = ActionResult(
                action_type=request.action_type,
                target=request.target,
                status=ActionStatus.failed,
                message=str(exc),
                policy_reasons=policy.reasons,
            )
        audit = self._audit(request, result, policy)
        result.audit_id = audit.id
        self._cache_idempotent(scoped_key, result)
        return result

    @staticmethod
    def _scoped_idempotency_key(request: ActionRequest) -> str | None:
        if not request.idempotency_key:
            return None
        return "|".join([request.actor_id, request.action_type, request.target.id, request.idempotency_key])

    def _audit(
        self,
        request: ActionRequest,
        result: ActionResult,
        policy: PolicyDecision | None,
        *,
        replayed: bool = False,
    ) -> AuditEntry:
        entry = AuditEntry(
            action_id=result.action_id,
            action_type=request.action_type,
            target=request.target,
            actor_id=request.actor_id,
            actor_roles=request.actor_roles,
            status=result.status,
            message=result.message,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            decision_id=request.decision_id,
            policy_effect=policy.effect if policy else None,
            policy_reasons=policy.reasons if policy else result.policy_reasons,
            effects=result.effects,
            replayed=replayed,
        )
        return self.audit_repository.append_audit(entry)

    def _cache_idempotent(self, scoped_key: str | None, result: ActionResult) -> None:
        if scoped_key:
            self.audit_repository.store_idempotent_result(scoped_key, result)

    def audits_for_action(self, action_id: str) -> list[AuditEntry]:
        return self.audit_repository.audits_for_action(action_id)

    def all_audits(self) -> list[AuditEntry]:
        return self.audit_repository.all_audits()

    def register_function(
        self,
        name: str,
        handler: FunctionHandler,
        *,
        input_model: type[BaseModel] | None = None,
        output_type: Any | None = None,
    ) -> None:
        self._functions[name] = FunctionDefinition(name, handler, input_model, output_type)

    def call_function(self, name: str, **kwargs: Any) -> Any:
        definition = self._functions.get(name)
        if not definition:
            raise KeyError(f"Unknown CEPIO function: {name}")
        validated_kwargs = kwargs
        if definition.input_model:
            validated = definition.input_model.model_validate(kwargs)
            validated_kwargs = validated.model_dump()
        result = definition.handler(runtime=self, **validated_kwargs)
        if definition.output_type is not None:
            return TypeAdapter(definition.output_type).validate_python(result)
        return result

    def save_decision(self, decision: Decision) -> Decision:
        self.get_object(decision.subject.id)
        return self.decision_repository.save_decision(decision)

    def get_decision(self, decision_id: str) -> Decision:
        decision = self.decision_repository.get_decision(decision_id)
        if not decision:
            raise KeyError(f"Unknown CEPIO decision: {decision_id}")
        return decision

    def list_decisions(self) -> list[Decision]:
        return self.decision_repository.list_decisions()

    def read_object_for_actor(self, object_id: str, roles: set[str]) -> OntologyObject:
        obj = self.get_object(object_id)
        if not self.policy_engine.can_read_type(roles, obj.type):
            raise AuthorizationError(f"Actor roles are not authorized to read object type {obj.type}")
        return self.policy_engine.filter_properties(roles, obj)
