from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime
from typing import Any, Iterator, Literal, Protocol

from pydantic import BaseModel, Field

from ...application_contract import ExecutionContext, SkillEvaluation, SkillInvocation
from ...application_runtime import build_application_service
from ...model import ActionRequest, ActionResult, ObjectRef, OntologyObject, PolicyDecision, PolicyEffect
from ...query import ObjectQuery, ObjectQueryResult
from ...runtime import AuthorizationError, CEPIORuntime

AuthMode = Literal[
    "agentic-identity",
    "project-managed-identity",
    "oauth2",
    "user-entra-token",
    "development",
]
PrincipalType = Literal["user", "agent", "service"]


class ActorContext(BaseModel):
    """Authenticated principal context injected by the hosting/authentication layer.

    Tool callers never supply this structure as MCP arguments. A Foundry/Entra
    adapter maps verified identity claims into CEPIO roles before tool execution.
    """

    subject_id: str
    roles: set[str] = Field(default_factory=set)
    principal_type: PrincipalType = "agent"
    auth_mode: AuthMode = "development"
    tenant_id: str | None = None
    client_id: str | None = None


class ActorProvider(Protocol):
    def current_actor(self) -> ActorContext: ...


class FixedActorProvider:
    """Reference/test provider. Do not use for a multi-user production endpoint."""

    def __init__(self, actor: ActorContext) -> None:
        self.actor = actor

    def current_actor(self) -> ActorContext:
        return self.actor.model_copy(deep=True)


_actor_context: ContextVar[ActorContext | None] = ContextVar("cepio_actor_context", default=None)


class ContextVarActorProvider:
    """Fail-closed provider for authenticated ASGI/Functions hosting adapters."""

    def current_actor(self) -> ActorContext:
        actor = _actor_context.get()
        if actor is None:
            raise AuthorizationError("No authenticated CEPIO actor context is available")
        return actor.model_copy(deep=True)

    @contextmanager
    def bind(self, actor: ActorContext) -> Iterator[None]:
        token: Token[ActorContext | None] = _actor_context.set(actor)
        try:
            yield
        finally:
            _actor_context.reset(token)


class EntraClaimsMapper:
    """Map already-verified Microsoft Entra claims into CEPIO actor context.

    Token verification belongs to the Azure hosting/authentication layer. This mapper
    deliberately accepts *verified claims*, not a bearer token, so CEPIO never
    accidentally becomes a permissive JWT decoder.
    """

    def __init__(
        self,
        *,
        role_map: dict[str, str] | None = None,
        group_role_map: dict[str, str] | None = None,
    ) -> None:
        self.role_map = role_map or {}
        self.group_role_map = group_role_map or {}

    def map_claims(
        self,
        claims: dict[str, Any],
        *,
        principal_type: PrincipalType,
        auth_mode: AuthMode,
    ) -> ActorContext:
        subject = claims.get("oid") or claims.get("sub")
        if not subject:
            raise AuthorizationError("Verified Entra claims do not contain oid/sub")

        mapped_roles = {
            self.role_map[role]
            for role in claims.get("roles", [])
            if role in self.role_map
        }
        mapped_roles.update(
            self.group_role_map[group]
            for group in claims.get("groups", [])
            if group in self.group_role_map
        )
        if not mapped_roles:
            raise AuthorizationError("Authenticated principal has no mapped CEPIO roles")

        return ActorContext(
            subject_id=str(subject),
            roles=mapped_roles,
            principal_type=principal_type,
            auth_mode=auth_mode,
            tenant_id=claims.get("tid"),
            client_id=claims.get("azp") or claims.get("appid"),
        )


class ActionRecommendation(BaseModel):
    action_type: str
    target: ObjectRef
    policy: PolicyDecision
    executable_by_current_actor: bool
    recommendation_permitted: bool


class CEPIOMCPGateway:
    """Policy-enforced CEPIO tool facade for Foundry/MCP clients.

    This class is transport-neutral by design. MCP, OpenAPI, tests, or future tool
    runtimes call the same governed methods. It never exposes repositories, Fabric
    adapters, SQL handles, or other bypass paths.
    """

    def __init__(self, runtime: CEPIORuntime, actor_provider: ActorProvider) -> None:
        self.runtime = runtime
        self.actor_provider = actor_provider
        self.application_service = build_application_service(runtime)

    def _actor(self) -> ActorContext:
        return self.actor_provider.current_actor()

    @staticmethod
    def _execution_context(actor: ActorContext) -> ExecutionContext:
        return ExecutionContext(
            actor_id=actor.subject_id,
            actor_roles=frozenset(actor.roles),
            tenant_id=actor.tenant_id,
        )

    def _authorize_object(self, obj: OntologyObject, actor: ActorContext) -> OntologyObject:
        if not self.runtime.policy_engine.can_read_type(actor.roles, obj.type):
            raise AuthorizationError(
                f"Actor {actor.subject_id} is not authorized to read object type {obj.type}"
            )
        return self.runtime.policy_engine.filter_properties(actor.roles, obj)

    def get_object(self, object_id: str) -> OntologyObject:
        actor = self._actor()
        return self._authorize_object(self.runtime.get_object(object_id), actor)

    def query_objects(self, query: ObjectQuery) -> ObjectQueryResult:
        actor = self._actor()
        if query.object_type is None:
            raise ValueError("Agent-facing CEPIO queries require an explicit object_type")
        if not self.runtime.policy_engine.can_read_type(actor.roles, query.object_type):
            raise AuthorizationError(
                f"Actor {actor.subject_id} is not authorized to query object type {query.object_type}"
            )
        method = getattr(self.runtime, "query_objects", None)
        if method is None:
            raise RuntimeError("Configured CEPIO runtime does not expose ObjectQuery")
        raw = method(query)
        visible = [
            self.runtime.policy_engine.filter_properties(actor.roles, obj)
            for obj in raw.items
            if self.runtime.policy_engine.can_read_type(actor.roles, obj.type)
        ]
        return ObjectQueryResult(
            items=visible,
            total=raw.total,
            offset=raw.offset,
            limit=raw.limit,
        )

    def get_state_at(
        self,
        object_id: str,
        *,
        valid_at: datetime | None = None,
        as_of_transaction: datetime | None = None,
    ) -> OntologyObject:
        if valid_at is None and as_of_transaction is None:
            raise ValueError("valid_at or as_of_transaction is required")
        actor = self._actor()
        if valid_at is not None:
            method = getattr(self.runtime, "get_object_valid_at", None)
            if method is None:
                raise RuntimeError("Configured CEPIO runtime does not support valid-time state")
            obj = method(object_id, valid_at, as_of_transaction=as_of_transaction)
        else:
            method = getattr(self.runtime, "get_object_at", None)
            if method is None:
                raise RuntimeError("Configured CEPIO runtime does not support transaction-time state")
            assert as_of_transaction is not None
            obj = method(object_id, as_of_transaction)
        return self._authorize_object(obj, actor)

    def explain_property(self, object_id: str, property_name: str) -> dict[str, Any]:
        actor = self._actor()
        obj = self.runtime.get_object(object_id)
        visible = self._authorize_object(obj, actor)

        registry = getattr(self.runtime, "property_registry", None)
        candidates = {property_name}
        if registry is not None:
            try:
                definition = registry.resolve(property_name)
                candidates.update({definition.iri, definition.qname, definition.local_name})
            except (KeyError, ValueError):
                pass
        if not any(candidate in visible.properties for candidate in candidates):
            raise AuthorizationError(
                f"Actor {actor.subject_id} is not authorized to read property {property_name}"
            )

        method = getattr(self.runtime, "explain_property", None)
        if method is None:
            raise RuntimeError("Configured CEPIO runtime does not expose property provenance")
        return method(object_id, property_name)

    def call_function(self, function_name: str, arguments: dict[str, Any]) -> Any:
        actor = self._actor()
        checker = getattr(self.runtime.policy_engine, "can_call_function", None)
        if checker is None or not checker(actor.roles, function_name):
            raise AuthorizationError(
                f"Actor {actor.subject_id} is not authorized to call function {function_name}"
            )
        return self.runtime.call_function(function_name, **arguments)

    def evaluate_skill(self, invocation: SkillInvocation) -> SkillEvaluation:
        actor = self._actor()
        return self.application_service.evaluate_skill(
            invocation,
            self._execution_context(actor),
        )

    def recommend_action(
        self,
        action_type: str,
        target_id: str,
        *,
        parameters: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        decision_id: str | None = None,
    ) -> ActionRecommendation:
        actor = self._actor()
        target = self.runtime.get_object(target_id)
        self._authorize_object(target, actor)
        definition = self.runtime._actions.get(action_type)  # governed registry; no adapter access
        if definition is None:
            raise KeyError(f"Unknown CEPIO action type: {action_type}")
        request = ActionRequest(
            action_type=action_type,
            target=ObjectRef(id=target.id, type=target.type),
            actor_id=actor.subject_id,
            actor_roles=actor.roles,
            parameters=parameters or {},
            correlation_id=correlation_id,
            decision_id=decision_id,
        )
        decision = self.runtime.policy_engine.evaluate_action(request, target, definition)
        recommend = decision.effect in {
            PolicyEffect.allow,
            PolicyEffect.recommend_only,
            PolicyEffect.approval_required,
        }
        executable = decision.effect == PolicyEffect.allow
        return ActionRecommendation(
            action_type=action_type,
            target=request.target,
            policy=decision,
            executable_by_current_actor=executable,
            recommendation_permitted=recommend,
        )

    def execute_action(
        self,
        action_type: str,
        target_id: str,
        *,
        parameters: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        decision_id: str | None = None,
    ) -> ActionResult:
        actor = self._actor()
        target = self.runtime.get_object(target_id)
        self._authorize_object(target, actor)
        request = ActionRequest(
            action_type=action_type,
            target=ObjectRef(id=target.id, type=target.type),
            actor_id=actor.subject_id,
            actor_roles=actor.roles,
            parameters=parameters or {},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            decision_id=decision_id,
        )
        return self.runtime.execute_action(request)
