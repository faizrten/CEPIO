from __future__ import annotations

import os

from datetime import datetime
from typing import Any
from typing import Literal

from ...application_contract import SkillInvocation
from ...application_contract import CEPIOApplicationService
from ...query import ObjectQuery
from ...runtime import AuthorizationError, CEPIORuntime
from .foundry_gateway import ActorProvider, CEPIOMCPGateway


def build_mcp_server(runtime: CEPIORuntime, actor_provider: ActorProvider):
    """Backward-compatible eight-tool MCP server for the standard CEPIO host."""
    return _build_mcp_server(CEPIOMCPGateway(runtime, actor_provider), include_actions=True)


def build_mcp_server_with_application_service(
    application_service: CEPIOApplicationService,
    actor_provider: ActorProvider,
    *,
    tool_profile: Literal["g1", "full"] = "g1",
):
    """Explicit protected-IQ composition; G1 defaults to six read/Skill tools.

    No tool-profile name comes from an agent request. Only the deployer supplies
    it during server construction. The existing public builder remains unchanged.
    """
    if tool_profile not in {"g1", "full"}:
        raise ValueError("Unsupported MCP tool profile")
    gateway = CEPIOMCPGateway.with_application_service(application_service, actor_provider)
    return _build_mcp_server(gateway, include_actions=tool_profile == "full")


def _enforce_mcp_client_tool_policy(gateway: CEPIOMCPGateway, tool: str) -> None:
    """Enforce deployment-pinned read-only OAuth clients on the canonical MCP endpoint.

    Client identity is obtained from the verified bearer token, NEVER tool inputs
    or untrusted HTTP headers. UI tool toggles are not an authorization boundary.
    Existing CEPIO per-actor/tenant/Skill/Action policy still applies separately.
    """
    configured = os.getenv("CEPIO_MCP_READ_ONLY_CLIENT_IDS", "")
    read_only_ids = {value.strip().lower() for value in configured.split(",") if value.strip()}
    if not read_only_ids:
        return
    actor = gateway.actor_provider.current_actor()
    if actor.client_id and actor.client_id.lower() in read_only_ids:
        raise AuthorizationError(
            f"MCP tool {tool} is disabled for this read-only client application"
        )


def _build_mcp_server(gateway: CEPIOMCPGateway, *, include_actions: bool):
    """Register the same governed MCP tools over one selected application service."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - exercised only without optional extra
        raise RuntimeError("Install CEPIO with the 'mcp' extra to build the MCP server") from exc

    mcp = MCPServer(
        "CEPIO Industrial Operating Gateway",
        instructions=(
            "Use CEPIO tools for governed industrial object queries, temporal state, "
            "lineage, functions, Skills and actions. Never infer authorization from the model. "
            "cepio_evaluate_skill may produce a governed Decision but does not grant action "
            "authority; cepio_execute_action remains a separate governed operation."
        ),
    )

    @mcp.tool(name="cepio_get_object", title="Get CEPIO object")
    def cepio_get_object(object_id: str) -> dict[str, Any]:
        """Read one CEPIO object after actor/type/property policy filtering."""
        return gateway.get_object(object_id).model_dump(mode="json")

    @mcp.tool(name="cepio_query_objects", title="Query CEPIO object set")
    def cepio_query_objects(query: ObjectQuery) -> dict[str, Any]:
        """Run the typed CEPIO ObjectQuery contract with actor policy filtering."""
        return gateway.query_objects(query).model_dump(mode="json")

    @mcp.tool(name="cepio_get_state_at", title="Get CEPIO point-in-time state")
    def cepio_get_state_at(
        object_id: str,
        valid_at: datetime | None = None,
        as_of_transaction: datetime | None = None,
    ) -> dict[str, Any]:
        """Read valid-time / transaction-time CEPIO state for an authorized object."""
        return gateway.get_state_at(
            object_id,
            valid_at=valid_at,
            as_of_transaction=as_of_transaction,
        ).model_dump(mode="json")

    @mcp.tool(name="cepio_explain_property", title="Explain CEPIO property lineage")
    def cepio_explain_property(object_id: str, property_name: str) -> dict[str, Any]:
        """Explain provenance for a property only when the actor may read that property."""
        return gateway.explain_property(object_id, property_name)

    @mcp.tool(name="cepio_call_function", title="Call governed CEPIO function")
    def cepio_call_function(function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke an explicitly policy-authorized deterministic CEPIO function."""
        _enforce_mcp_client_tool_policy(gateway, "cepio_call_function")
        value = gateway.call_function(function_name, arguments)
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        return {"result": value}

    @mcp.tool(name="cepio_evaluate_skill", title="Evaluate governed CEPIO Skill")
    def cepio_evaluate_skill(invocation: SkillInvocation) -> dict[str, Any]:
        """Evaluate one admitted executable Skill through the shared application contract."""
        _enforce_mcp_client_tool_policy(gateway, "cepio_evaluate_skill")
        return gateway.evaluate_skill(invocation).model_dump(mode="json")

    if include_actions:

        @mcp.tool(name="cepio_recommend_action", title="Evaluate CEPIO action recommendation")
        def cepio_recommend_action(
            action_type: str,
            target_id: str,
            parameters: dict[str, Any] | None = None,
            correlation_id: str | None = None,
            decision_id: str | None = None,
        ) -> dict[str, Any]:
            """Evaluate whether the actor may recommend/execute an action without executing it."""
            _enforce_mcp_client_tool_policy(gateway, "cepio_recommend_action")
            return gateway.recommend_action(
                action_type,
                target_id,
                parameters=parameters,
                correlation_id=correlation_id,
                decision_id=decision_id,
            ).model_dump(mode="json")

        @mcp.tool(name="cepio_execute_action", title="Execute governed CEPIO action")
        def cepio_execute_action(
            action_type: str,
            target_id: str,
            parameters: dict[str, Any] | None = None,
            idempotency_key: str | None = None,
            correlation_id: str | None = None,
            decision_id: str | None = None,
        ) -> dict[str, Any]:
            """Execute a CEPIO action through runtime policy, preconditions and audit controls."""
            _enforce_mcp_client_tool_policy(gateway, "cepio_execute_action")
            return gateway.execute_action(
                action_type,
                target_id,
                parameters=parameters,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                decision_id=decision_id,
            ).model_dump(mode="json")

    return mcp
