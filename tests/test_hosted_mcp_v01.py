from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft import hosted_mcp
from cepio.integrations.microsoft.foundry_gateway import ContextVarActorProvider
from cepio.integrations.microsoft.hosted_mcp import (
    MCPActorBindingMiddleware,
    actor_from_headers,
    build_hosted_mcp,
)


def test_mcp_dev_identity_is_host_injected_and_requires_a_role(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    actor = actor_from_headers(
        Headers(
            {
                "X-CEPIO-Dev-Actor": "agent-01",
                "X-CEPIO-Dev-Roles": "ai_agent_recommender,maintenance_engineer",
            }
        )
    )
    assert actor.subject_id == "agent-01"
    assert actor.roles == {"ai_agent_recommender", "maintenance_engineer"}
    assert actor.auth_mode == "development"

    with pytest.raises(HTTPException) as exc_info:
        actor_from_headers(Headers({"X-CEPIO-Dev-Actor": "unprivileged"}))
    assert exc_info.value.status_code == 403


def test_mcp_transport_security_preserves_explicit_hosts_and_azure_hostname(monkeypatch):
    monkeypatch.setenv("CEPIO_MCP_ALLOWED_HOSTS", "mcp.example.com")
    monkeypatch.setenv("WEBSITE_HOSTNAME", "cepio-demo.example.azurewebsites.net")
    monkeypatch.setenv("CEPIO_MCP_ALLOWED_ORIGINS", "https://studio.example.com")

    settings = hosted_mcp._transport_security()

    assert settings.enable_dns_rebinding_protection is True
    assert settings.allowed_hosts == [
        "mcp.example.com",
        "cepio-demo.example.azurewebsites.net",
        "cepio-demo.example.azurewebsites.net:*",
    ]
    assert settings.allowed_origins == ["https://studio.example.com"]


def test_mcp_entra_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")

    with pytest.raises(HTTPException) as exc_info:
        actor_from_headers(Headers())

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_mcp_entra_rejects_authenticated_actor_without_cepio_role(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")

    class FakeValidator:
        def __init__(self, _settings):
            pass

        def validate(self, token: str):
            assert token == "no-role-token"
            return SimpleNamespace(
                actor_id="actor-no-role",
                roles=set(),
                tenant_id="tenant-01",
                claims={"oid": "actor-no-role"},
            )

    monkeypatch.setattr(hosted_mcp, "EntraTokenValidator", FakeValidator)

    with pytest.raises(HTTPException) as exc_info:
        actor_from_headers(Headers({"Authorization": "Bearer no-role-token"}))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "mcp_role_required"


def test_mcp_entra_maps_verified_application_identity(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")

    class FakeValidator:
        def __init__(self, _settings):
            pass

        def validate(self, token: str):
            assert token == "service-token"
            return SimpleNamespace(
                actor_id="agent-object-id",
                roles={"ai_agent_recommender"},
                tenant_id="tenant-01",
                claims={
                    "idtyp": "app",
                    "roles": ["ai_agent_recommender"],
                    "azp": "foundry-agent-client",
                },
            )

    monkeypatch.setattr(hosted_mcp, "EntraTokenValidator", FakeValidator)

    actor = actor_from_headers(Headers({"Authorization": "Bearer service-token"}))

    assert actor.subject_id == "agent-object-id"
    assert actor.roles == {"ai_agent_recommender"}
    assert actor.principal_type == "service"
    assert actor.auth_mode == "agentic-identity"
    assert actor.tenant_id == "tenant-01"
    assert actor.client_id == "foundry-agent-client"


def test_mcp_actor_binding_middleware_binds_verified_context(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    provider = ContextVarActorProvider()

    async def inner(scope, receive, send):
        actor = provider.current_actor()
        body = f"{actor.subject_id}|{','.join(sorted(actor.roles))}".encode()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": body})

    host = FastAPI()
    host.mount("/", MCPActorBindingMiddleware(inner, provider))
    client = TestClient(host)

    denied = client.get("/")
    assert denied.status_code == 403

    allowed = client.get(
        "/",
        headers={
            "X-CEPIO-Dev-Actor": "agent-02",
            "X-CEPIO-Dev-Roles": "ai_agent_recommender",
        },
    )
    assert allowed.status_code == 200
    assert allowed.text == "agent-02|ai_agent_recommender"


def test_mcp_actor_binding_passes_non_http_scope_through(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    provider = ContextVarActorProvider()
    observed: list[str] = []

    async def inner(scope, receive, send):
        observed.append(scope["type"])

    async def receive():
        return {"type": "websocket.disconnect"}

    async def send(_message):
        return None

    middleware = MCPActorBindingMiddleware(inner, provider)
    asyncio.run(middleware({"type": "websocket"}, receive, send))

    assert observed == ["websocket"]


def test_hosted_mcp_session_manager_runs_for_authenticated_http(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    runtime = build_runtime()
    server, mcp_http_app = build_hosted_mcp(runtime)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with server.session_manager.run():
            yield

    host = FastAPI(lifespan=lifespan)
    host.mount("/", mcp_http_app)

    headers = {
        "X-CEPIO-Dev-Actor": "agent-03",
        "X-CEPIO-Dev-Roles": "ai_agent_recommender",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    with TestClient(host) as client:
        anonymous = client.post("/mcp", json={})
        assert anonymous.status_code == 403

        # An intentionally malformed protocol payload is sufficient to prove that
        # authentication passed, `/mcp` routed, and the MCP session manager was live.
        # A dead mounted manager fails with HTTP 500 before protocol validation.
        authenticated = client.post("/mcp", headers=headers, json={})
        assert authenticated.status_code < 500
        assert authenticated.status_code not in {401, 403, 404}


def test_restart_safe_mcp_mount_fails_closed_before_lifespan(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    from cepio.host_api import _RestartSafeMCPMount

    host = FastAPI()
    host.mount("/", _RestartSafeMCPMount())
    response = TestClient(host).get("/")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "mcp_not_ready"


def test_deployed_host_keeps_rest_openapi_and_mcp_out_of_rest_contract(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    from cepio.host_api import app

    # Enter TestClient as a context so the deployed host lifespan starts the
    # restart-safe MCP transport/session manager before `/mcp` is exercised.
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200

        anonymous_mcp = client.post("/mcp", json={})
        assert anonymous_mcp.status_code == 403

        public_paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/health" in public_paths
        assert "/mcp" not in public_paths
