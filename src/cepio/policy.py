from __future__ import annotations

from pathlib import Path
from typing import Protocol

import yaml

from .model import ActionRequest, OntologyObject, PolicyDecision, PolicyEffect
from .registry import TypeRegistry


class ActionDefinitionLike(Protocol):
    name: str
    allowed_roles: set[str]
    requires_human_approval: bool


class PolicyEngine(Protocol):
    def evaluate_action(
        self, request: ActionRequest, target: OntologyObject, definition: ActionDefinitionLike
    ) -> PolicyDecision: ...

    def can_read_type(self, roles: set[str], object_type: str) -> bool: ...

    def can_read_object(self, roles: set[str], obj: OntologyObject) -> bool: ...

    def filter_properties(
        self, roles: set[str], obj: OntologyObject
    ) -> OntologyObject: ...

    def can_call_function(self, roles: set[str], function_name: str) -> bool: ...


class RolePolicyEngine:
    """Reference policy engine.

    This implementation is intentionally replaceable by Entra, OPA, Cedar or another
    enterprise authorization service. It supports action RBAC, recommend-only agent
    roles, object-type read controls, object sharing scopes, property allowlists, and
    explicit function-call permissions for governed tool/runtime surfaces.
    """

    def __init__(
        self, policies: dict[str, dict] | None = None, type_registry: TypeRegistry | None = None
    ) -> None:
        self.policies = policies or {}
        self.type_registry = type_registry

    @classmethod
    def from_yaml(
        cls, path: str | Path, *, type_registry: TypeRegistry | None = None
    ) -> "RolePolicyEngine":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return cls(raw.get("policies", {}), type_registry=type_registry)

    def evaluate_action(
        self, request: ActionRequest, target: OntologyObject, definition: ActionDefinitionLike
    ) -> PolicyDecision:
        roles = request.actor_roles
        if definition.allowed_roles and roles.intersection(definition.allowed_roles):
            if definition.requires_human_approval and not self._has_human_role(roles):
                return PolicyDecision(
                    effect=PolicyEffect.approval_required,
                    reasons=["Action requires a human approval role"],
                    requires_human_approval=True,
                )
            return PolicyDecision(effect=PolicyEffect.allow, reasons=["Actor role permits action"])

        recommendable = {
            role
            for role in roles
            if request.action_type in set(self.policies.get(role, {}).get("can_recommend", []))
        }
        if recommendable:
            return PolicyDecision(
                effect=PolicyEffect.recommend_only,
                reasons=[f"Role(s) {sorted(recommendable)} may recommend but not execute this action"],
            )

        return PolicyDecision(
            effect=PolicyEffect.deny,
            reasons=[f"No actor role is permitted to execute {request.action_type}"],
        )

    def can_read_type(self, roles: set[str], object_type: str) -> bool:
        if not self.policies:
            return True
        for role in roles:
            rule = self.policies.get(role, {})
            read_types = set(rule.get("read_types", []))
            if "*" in read_types or object_type in read_types:
                return True
            if self.type_registry and any(self.type_registry.is_a(object_type, allowed) for allowed in read_types):
                return True
        return False

    def can_read_object(self, roles: set[str], obj: OntologyObject) -> bool:
        if not self.can_read_type(roles, obj.type):
            return False

        scope = obj.properties.get("sharingScope", obj.properties.get("sharing_scope"))
        if scope is None:
            return True
        scopes = {str(scope)} if not isinstance(scope, (list, tuple, set)) else {str(value) for value in scope}

        for role in roles:
            allowed = set(self.policies.get(role, {}).get("read_scopes", []))
            if "*" in allowed or allowed.intersection(scopes):
                return True
        return False

    def filter_properties(self, roles: set[str], obj: OntologyObject) -> OntologyObject:
        allowed: set[str] | None = None
        unrestricted = False
        for role in roles:
            rule = self.policies.get(role, {})
            property_rules = rule.get("read_properties", {})
            prop_rule = property_rules.get(obj.type)
            if prop_rule is None and self.type_registry:
                inherited_rules = [
                    value
                    for declared_type, value in property_rules.items()
                    if self.type_registry.is_a(obj.type, declared_type)
                ]
                if "*" in inherited_rules:
                    prop_rule = "*"
                else:
                    merged: list[str] = []
                    for value in inherited_rules:
                        if isinstance(value, list):
                            merged.extend(value)
                    prop_rule = merged or None
            if prop_rule == "*":
                unrestricted = True
                break
            if isinstance(prop_rule, list):
                allowed = (allowed or set()).union(prop_rule)
        if unrestricted or allowed is None:
            return obj.model_copy(deep=True)
        filtered = obj.model_copy(deep=True)
        filtered.properties = {k: v for k, v in obj.properties.items() if k in allowed}
        return filtered

    def can_call_function(self, roles: set[str], function_name: str) -> bool:
        if not self.policies:
            return True
        for role in roles:
            allowed = set(self.policies.get(role, {}).get("functions", []))
            if "*" in allowed or function_name in allowed:
                return True
        return False

    @staticmethod
    def _has_human_role(roles: set[str]) -> bool:
        return any(not r.startswith("ai_") and "agent" not in r for r in roles)
