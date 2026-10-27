from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from ...application_contract import SkillInvocation
from ...application_contract import CEPIOApplicationService
from ...query import ObjectQuery
from ...runtime import CEPIORuntime
from .foundry_gateway import ActorProvider, CEPIOMCPGateway


def build_mcp_server(runtime: CEPIORuntime, actor_provider: ActorProvider):
    """Backward-compatible eight-tool MCP server for the standard CEPIO host."""
    return _build_mcp_server(CEPIOMCPGateway(runtime, actor_provider), include_actions=True)


def build_copilot_read_only_mcp_server(runtime: CEPIORuntime, actor_provider: ActorProvider):
    """Dedicated four-tool surface. Tool visibility is deployment pinned, not agent-chosen."""
    return _build_mcp_server(
        CEPIOMCPGateway(runtime, actor_provider),
        include_actions=False,
        include_analysis=False,
    )


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


def _build_mcp_server(
    gateway: CEPIOMCPGateway, *, include_actions: bool, include_analysis: bool = True
):
    """Register the same governed MCP tools over one selected application service."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - exercised only without optional extra
        raise RuntimeError("Install CEPIO with the 'mcp' extra to build the MCP server") from exc

    mcp = MCPServer(
        "CEPIO Industrial Operating Gateway",
        instructions=(
            "Read-only CEPIO investigation tools: object query, point-in-time state and "
            "property provenance. Never treat model output as source evidence or grant "
            "execution authority."
            if not include_analysis
            else (
                "Use CEPIO tools for governed industrial object queries, temporal state, "
                "lineage, functions, Skills and actions. Never infer authorization from the model. "
                "cepio_evaluate_skill may produce a governed Decision but does not grant action "
                "authority; cepio_execute_action remains a separate governed operation."
            )
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

    if include_analysis:

        @mcp.tool(name="cepio_call_function", title="Call governed CEPIO function")
        def cepio_call_function(function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            """Invoke an explicitly policy-authorized deterministic CEPIO function."""
            value = gateway.call_function(function_name, arguments)
            if hasattr(value, "model_dump"):
                value = value.model_dump(mode="json")
            return {"result": value}

        @mcp.tool(name="cepio_evaluate_skill", title="Evaluate governed CEPIO Skill")
        def cepio_evaluate_skill(invocation: SkillInvocation) -> dict[str, Any]:
            """Evaluate one admitted executable Skill through the shared application contract."""
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
            return gateway.execute_action(
                action_type,
                target_id,
                parameters=parameters,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                decision_id=decision_id,
            ).model_dump(mode="json")

    return mcp
