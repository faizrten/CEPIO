"""Bounded Copilot Studio read-only MCP profile: tool discovery and auth gates.

This is protocol/unit qualification with synthetic actors, not a live Microsoft
Copilot Studio, Entra consent or customer-data integration test.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft import hosted_mcp
from cepio.integrations.microsoft.foundry_gateway import (
    ActorContext,
    FixedActorProvider,
)
from cepio.integrations.microsoft.foundry_mcp import (
    build_copilot_read_only_mcp_server,
    build_mcp_server,
)


READ_ONLY_TOOLS = {
    "cepio_get_object",
    "cepio_query_objects",
    "cepio_get_state_at",
    "cepio_explain_property",
}


def test_copilot_read_only_inprocess_discovers_no_mutation_or_skill_tools():
    from mcp import Client

    runtime = build_runtime()
    provider = FixedActorProvider(
        ActorContext(
            subject_id="copilot-synthetic-reader",
            roles={"maintenance_engineer"},
            tenant_id="test-tenant",
        )
    )
    server = build_copilot_read_only_mcp_server(runtime, provider)
    standard = build_mcp_server(runtime, provider)

    async def check():
        async with Client(server) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert names == READ_ONLY_TOOLS
        async with Client(standard) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert "cepio_execute_action" in names
            assert "cepio_evaluate_skill" in names

    asyncio.run(check())


def test_copilot_hosted_endpoint_is_separate_authenticated_and_read_only(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")

    class FakeValidator:
        def __init__(self, settings):
            pass

        def validate(self, token):
            if token != "synthetic-copilot-reader":
                raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})
            return SimpleNamespace(
                actor_id="test-reader",
                tenant_id="test-tenant",
                roles={"maintenance_engineer"},
                claims={"oid": "test-reader", "scp": "access_as_user"},
            )

    monkeypatch.setattr(hosted_mcp, "EntraTokenValidator", FakeValidator)
    from cepio.host_api import app

    headers = {
        "Authorization": "Bearer synthetic-copilot-reader",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    with TestClient(app) as client:
        for auth_headers in ({}, {"X-CEPIO-Dev-Roles": "cepio_admin"}):
            response = client.post("/copilot/mcp", json={}, headers=auth_headers)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"

        init = client.post(
            "/copilot/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "copilot-p0-test", "version": "1"},
                },
            },
        )
        assert init.status_code == 200
        headers["MCP-Protocol-Version"] = init.json()["result"]["protocolVersion"]

        listed = client.post(
            "/copilot/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert listed.status_code == 200
        assert {tool["name"] for tool in listed.json()["result"]["tools"]} == READ_ONLY_TOOLS

        standard_init = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "regression-test", "version": "1"},
                },
            },
        )
        assert standard_init.status_code == 200
        standard_headers = dict(headers)
        standard_headers["MCP-Protocol-Version"] = standard_init.json()["result"]["protocolVersion"]
        standard_list = client.post(
            "/mcp",
            headers=standard_headers,
            json={"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
        )
        assert standard_list.status_code == 200
        assert "cepio_execute_action" in {
            tool["name"] for tool in standard_list.json()["result"]["tools"]
        }
        assert "/copilot/mcp" not in client.get("/openapi.json").json()["paths"]
