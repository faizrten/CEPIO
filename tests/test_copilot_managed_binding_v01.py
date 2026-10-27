"""One canonical CEPIO /mcp: Copilot client restrictions are enforced server-side.

These are synthetic Entra/protocol tests, not actual Copilot Studio or live
customer-tenancy qualification. No actual access tokens or clients are provisioned.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from cepio.application_contract import SkillInvocation
from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft import hosted_mcp
from cepio.integrations.microsoft.foundry_gateway import ActorContext, FixedActorProvider
from cepio.integrations.microsoft.foundry_mcp import (
    _enforce_mcp_client_tool_policy,
    build_mcp_server,
)
from cepio.model import ObjectRef
from cepio.runtime import AuthorizationError


READ_TOOLS = {
    "cepio_get_object",
    "cepio_query_objects",
    "cepio_get_state_at",
    "cepio_explain_property",
}
RESTRICTED_TOOLS = {
    "cepio_call_function",
    "cepio_evaluate_skill",
    "cepio_recommend_action",
    "cepio_execute_action",
}


def _gateway(client_id: str):
    from cepio.integrations.microsoft.foundry_gateway import CEPIOMCPGateway

    actor = ActorContext(
        subject_id="synthetic-admin",
        roles={"cepio_admin", "maintenance_engineer"},
        client_id=client_id,
        auth_mode="oauth2",
        tenant_id="test-tenant",
    )
    return CEPIOMCPGateway(build_runtime(), FixedActorProvider(actor))


def test_read_only_client_id_blocks_advanced_tools_even_with_admin_roles(monkeypatch):
    from mcp import Client

    monkeypatch.setenv("CEPIO_MCP_READ_ONLY_CLIENT_IDS", "COPILOT-CLIENT,another-client")
    gateway = _gateway("copilot-client")
    server = build_mcp_server(gateway.runtime, gateway.actor_provider)

    async def check():
        async with Client(server, raise_exceptions=False) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
            # A single consistent MCP schema is advertised; the agent disables
            # unneeded tools and CEPIO enforces the client restriction on calls.
            assert names == READ_TOOLS | RESTRICTED_TOOLS
            inv = SkillInvocation(
                skill_id="synthetic.reliability.review",
                subject=ObjectRef(id="EQ-07", type="Equipment"),
                evidence=[],
            )
            forbidden_calls = {
                "cepio_call_function": {"function_name": "calculateAssetRisk", "arguments": {}},
                "cepio_evaluate_skill": {"invocation": inv.model_dump(mode="json")},
                "cepio_recommend_action": {
                    "action_type": "maintenance_review",
                    "target_id": "EQ-07",
                },
                "cepio_execute_action": {
                    "action_type": "maintenance_review",
                    "target_id": "EQ-07",
                },
            }
            for tool_name, arguments in forbidden_calls.items():
                result = await client.call_tool(tool_name, arguments)
                assert result.is_error, tool_name
                assert f"error executing tool {tool_name}" in str(result.content).lower()

    asyncio.run(check())


def test_unlisted_client_keeps_existing_cepio_policy_path(monkeypatch):
    monkeypatch.setenv("CEPIO_MCP_READ_ONLY_CLIENT_IDS", "copilot-client")
    _enforce_mcp_client_tool_policy(_gateway("foundry-client"), "cepio_execute_action")
    with pytest.raises(AuthorizationError, match="read-only client"):
        _enforce_mcp_client_tool_policy(_gateway("CoPiLoT-ClIeNt"), "cepio_execute_action")


def test_single_hosted_mcp_uses_verified_entra_client_id(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")
    monkeypatch.setenv("CEPIO_MCP_READ_ONLY_CLIENT_IDS", "copilot-client")

    class FakeValidator:
        def __init__(self, _settings):
            pass

        def validate(self, token):
            if token == "synthetic-copilot":
                return SimpleNamespace(
                    actor_id="synthetic-admin",
                    tenant_id="test-tenant",
                    roles={"cepio_admin", "maintenance_engineer"},
                    claims={
                        "oid": "synthetic-admin",
                        "tid": "test-tenant",
                        "scp": "access_as_user",
                        "azp": "copilot-client",
                    },
                )
            if token == "synthetic-no-role":
                return SimpleNamespace(
                    actor_id="unmapped",
                    tenant_id="test-tenant",
                    roles=set(),
                    claims={"oid": "unmapped", "azp": "copilot-client"},
                )
            raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    monkeypatch.setattr(hosted_mcp, "EntraTokenValidator", FakeValidator)
    from cepio.host_api import app

    headers = {
        "Authorization": "Bearer synthetic-copilot",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    with TestClient(app) as client:
        for auth_headers in ({}, {"X-CEPIO-Dev-Roles": "cepio_admin"}):
            denied = client.post("/mcp", headers=auth_headers, json={})
            assert denied.status_code == 401
            assert denied.headers["www-authenticate"] == "Bearer"

        forbidden_role = client.post(
            "/mcp", headers={"Authorization": "Bearer synthetic-no-role"}, json={}
        )
        assert forbidden_role.status_code == 403

        init = client.post(
            "/mcp",
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
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert listed.status_code == 200
        assert {tool["name"] for tool in listed.json()["result"]["tools"]} == (
            READ_TOOLS | RESTRICTED_TOOLS
        )

        blocked = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "cepio_call_function",
                    "arguments": {"function_name": "calculateAssetRisk", "arguments": {}},
                },
            },
        )
        assert blocked.status_code == 200
        assert blocked.json()["result"]["isError"] is True
        assert "error executing tool cepio_call_function" in str(\n            blocked.json()["result"]["content"]\n        ).lower()

        missing = client.post("/copilot/mcp", headers=headers, json={})
        assert missing.status_code == 404
        assert "/mcp" not in client.get("/openapi.json").json()["paths"]
        assert "/copilot/mcp" not in client.get("/openapi.json").json()["paths"]
