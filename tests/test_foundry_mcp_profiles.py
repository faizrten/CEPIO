from __future__ import annotations

import asyncio

import pytest

from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft.foundry_gateway import (
    ActorContext,
    FixedActorProvider,
)
from cepio.integrations.microsoft.foundry_mcp import build_mcp_server


def _actor() -> ActorContext:
    return ActorContext(
        subject_id="agent-foundry-g1",
        roles={"ai_agent_recommender"},
        principal_type="agent",
        auth_mode="agentic-identity",
        tenant_id="tenant-g1",
        client_id="agent-g1-client",
    )


def test_recommendation_only_profile_excludes_action_execution_tool():
    from mcp import Client

    server = build_mcp_server(
        build_runtime(),
        FixedActorProvider(_actor()),
        tool_profile="recommendation-only",
    )

    async def _exercise() -> None:
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert "cepio_evaluate_skill" in names
            assert "cepio_recommend_action" in names
            assert "cepio_execute_action" not in names
            assert names == {
                "cepio_get_object",
                "cepio_query_objects",
                "cepio_get_state_at",
                "cepio_explain_property",
                "cepio_call_function",
                "cepio_evaluate_skill",
                "cepio_recommend_action",
            }

    asyncio.run(_exercise())


def test_full_profile_preserves_action_execution_tool():
    from mcp import Client

    server = build_mcp_server(
        build_runtime(),
        FixedActorProvider(_actor()),
        tool_profile="full",
    )

    async def _exercise() -> None:
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert "cepio_execute_action" in names
            assert len(names) == 8

    asyncio.run(_exercise())


def test_unknown_tool_profile_fails_closed():
    with pytest.raises(ValueError, match="Unsupported CEPIO MCP tool profile"):
        build_mcp_server(
            build_runtime(),
            FixedActorProvider(_actor()),
            tool_profile="autonomous",  # type: ignore[arg-type]
        )
