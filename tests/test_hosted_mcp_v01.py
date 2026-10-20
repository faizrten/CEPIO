from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from cepio.bootstrap import build_runtime
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
