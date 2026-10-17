from __future__ import annotations

from typing import Any

from .model import ActionRequest, FunctionInvocation, ObjectRef
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
            {"name": "cepio_execute_action", "description": "Attempt a governed CEPIO action. Policy may reject or constrain execution.", "inputSchema": {"type": "object", "properties": {"action_type": {"type": "string"}, "target_id": {"type": "string"}, "target_type": {"type": "string"}, "parameters": {"type": "object"}, "idempotency_key": {"type": ["string", "null"]}}, "required": ["action_type", "target_id", "target_type"]}},
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
        if name == "cepio_execute_action":
            request = ActionRequest(action_type=arguments["action_type"], target=ObjectRef(id=arguments["target_id"], type=arguments["target_type"]), actor_id=self.actor_id, actor_roles=self.actor_roles, parameters=arguments.get("parameters", {}), idempotency_key=arguments.get("idempotency_key"))
            try:
                result = self.runtime.execute_action(request)
                return result.model_dump(mode="json")
            except AuthorizationError as exc:
                if exc.result:
                    return exc.result.model_dump(mode="json")
                raise
        raise KeyError(f"Unknown CEPIO MCP tool: {name}")
