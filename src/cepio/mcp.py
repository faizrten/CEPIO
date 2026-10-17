from __future__ import annotations

from typing import Any

from .model import ActionRequest, Decision, FunctionInvocation, ObjectRef
from .runtime import AuthorizationError, CEPIORuntime


class MCPFacade:
    """MCP-ready facade without binding CEPIO core to a specific MCP SDK."""

    def __init__(self, runtime: CEPIORuntime, *, actor_id: str, actor_roles: set[str]) -> None:
        self.runtime = runtime
        self.actor_id = actor_id
        self.actor_roles = actor_roles

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "cepio_get_object", "description": "Read an authorized CEPIO object by ID", "inputSchema": {"type": "object", "properties": {"object_id": {"type": "string"}}, "required": ["object_id"]}},
            {"name": "cepio_neighbors", "description": "Traverse outgoing CEPIO relationships", "inputSchema": {"type": "object", "properties": {"object_id": {"type": "string"}, "relationship_type": {"type": ["string", "null"]}}, "required": ["object_id"]}},
            {"name": "cepio_call_function", "description": "Invoke an authorized registered CEPIO business function", "inputSchema": {"type": "object", "properties": {"function": {"type": "string"}, "arguments": {"type": "object"}}, "required": ["function", "arguments"]}},
            {"name": "cepio_save_decision", "description": "Persist an authorized named CEPIO decision recommendation", "inputSchema": {"type": "object", "properties": {"decision_type": {"type": "string"}, "subject_id": {"type": "string"}, "subject_type": {"type": "string"}, "problem": {"type": "string"}, "observations": {"type": "array", "items": {"type": "string"}}, "recommendation": {"type": "string"}, "recommended_action": {"type": ["string", "null"]}, "confidence": {"type": ["number", "null"]}}, "required": ["decision_type", "subject_id", "subject_type", "problem", "recommendation"]}},
            {"name": "cepio_execute_action", "description": "Attempt a governed CEPIO action. Policy may reject or constrain execution.", "inputSchema": {"type": "object", "properties": {"action_type": {"type": "string"}, "target_id": {"type": "string"}, "target_type": {"type": "string"}, "parameters": {"type": "object"}, "idempotency_key": {"type": ["string", "null"]}, "decision_id": {"type": ["string", "null"]}}, "required": ["action_type", "target_id", "target_type"]}},
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "cepio_get_object":
            obj = self.runtime.read_object_for_actor(arguments["object_id"], self.actor_roles)
            return obj.model_dump(mode="json")
        if name == "cepio_neighbors":
            start = self.runtime.read_object_for_actor(arguments["object_id"], self.actor_roles)
            neighbors = self.runtime.neighbors(start.id, arguments.get("relationship_type"))
            visible = []
            for obj in neighbors:
                if self.runtime.policy_engine.can_read_type(self.actor_roles, obj.type):
                    visible.append(self.runtime.policy_engine.filter_properties(self.actor_roles, obj).model_dump(mode="json"))
            return {"objects": visible}
        if name == "cepio_call_function":
            invocation = FunctionInvocation.model_validate(arguments)
            if not self.runtime.policy_engine.can_call_function(self.actor_roles, invocation.function):
                raise AuthorizationError(
                    f"Actor roles are not authorized to call function {invocation.function}"
                )
            value = self.runtime.call_function(invocation.function, **invocation.arguments)
            if hasattr(value, "model_dump"):
                value = value.model_dump(mode="json")
            return {"result": value}
        if name == "cepio_save_decision":
            decision_type = str(arguments["decision_type"])
            if not self.runtime.policy_engine.can_propose_decision(self.actor_roles, decision_type):
                raise AuthorizationError(
                    f"Actor roles are not authorized to propose decision {decision_type}"
                )
            self.runtime.read_object_for_actor(arguments["subject_id"], self.actor_roles)
            decision = Decision(
                decision_type=decision_type,
                subject=ObjectRef(id=arguments["subject_id"], type=arguments["subject_type"]),
                problem=arguments["problem"],
                observations=arguments.get("observations", []),
                recommendation=arguments["recommendation"],
                recommended_action=arguments.get("recommended_action"),
                confidence=arguments.get("confidence"),
                created_by=self.actor_id,
            )
            return self.runtime.save_decision(decision).model_dump(mode="json")
        if name == "cepio_execute_action":
            request = ActionRequest(action_type=arguments["action_type"], target=ObjectRef(id=arguments["target_id"], type=arguments["target_type"]), actor_id=self.actor_id, actor_roles=self.actor_roles, parameters=arguments.get("parameters", {}), idempotency_key=arguments.get("idempotency_key"), decision_id=arguments.get("decision_id"))
            try:
                result = self.runtime.execute_action(request)
                return result.model_dump(mode="json")
            except AuthorizationError as exc:
                if exc.result:
                    return exc.result.model_dump(mode="json")
                raise
        raise KeyError(f"Unknown CEPIO MCP tool: {name}")
