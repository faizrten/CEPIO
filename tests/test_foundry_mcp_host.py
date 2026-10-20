from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from cepio.auth import ActorContext as AuthActorContext
from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft import foundry_mcp_host as host
from cepio.integrations.microsoft.foundry_gateway import (
    ContextVarActorProvider,
    EntraClaimsMapper,
)
from cepio.integrations.microsoft.foundry_mcp_host import EntraMCPAuthMiddleware


class FakeValidator:
    def __init__(self, claims: dict):
        self.claims = claims
        self.tokens: list[str] = []

    def validate(self, token: str) -> AuthActorContext:
        self.tokens.append(token)
        return AuthActorContext(
            actor_id=str(self.claims.get("oid", "agent-1")),
            roles=set(self.claims.get("roles", [])),
            tenant_id=self.claims.get("tid"),
            claims=self.claims,
        )


class RejectingValidator:
    def validate(self, token: str) -> AuthActorContext:
        raise HTTPException(status_code=401, detail="invalid token")


def _app(provider: ContextVarActorProvider):
    async def downstream(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        actor = provider.current_actor()
        response = JSONResponse(
            {
                "subject_id": actor.subject_id,
                "roles": sorted(actor.roles),
                "auth_mode": actor.auth_mode,
                "principal_type": actor.principal_type,
            }
        )
        await response(scope, receive, send)

    return downstream


def test_entra_mcp_auth_binds_mapped_agent_identity():
    provider = ContextVarActorProvider()
    validator = FakeValidator(
        {
            "oid": "foundry-agent-123",
            "tid": "tenant-1",
            "azp": "agent-client-1",
            "roles": ["CEPIO.Agent.Recommender"],
        }
    )
    app = EntraMCPAuthMiddleware(
        _app(provider),
        token_validator=validator,
        claims_mapper=EntraClaimsMapper(
            role_map={"CEPIO.Agent.Recommender": "ai_agent_recommender"}
        ),
        actor_provider=provider,
    )

    with TestClient(app) as client:
        response = client.get("/", headers={"Authorization": "Bearer token-1"})

    assert response.status_code == 200
    assert validator.tokens == ["token-1"]
    assert response.json() == {
        "subject_id": "foundry-agent-123",
        "roles": ["ai_agent_recommender"],
        "auth_mode": "agentic-identity",
        "principal_type": "agent",
    }


def test_entra_mcp_auth_requires_bearer_token():
    provider = ContextVarActorProvider()
    app = EntraMCPAuthMiddleware(
        _app(provider),
        token_validator=FakeValidator({}),
        claims_mapper=EntraClaimsMapper(role_map={"role": "ai_agent_recommender"}),
        actor_provider=provider,
    )

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"
    assert response.headers["www-authenticate"] == "Bearer"


def test_entra_mcp_auth_rejects_invalid_token():
    provider = ContextVarActorProvider()
    app = EntraMCPAuthMiddleware(
        _app(provider),
        token_validator=RejectingValidator(),
        claims_mapper=EntraClaimsMapper(role_map={"role": "ai_agent_recommender"}),
        actor_provider=provider,
    )

    with TestClient(app) as client:
        response = client.get("/", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_token",
        "message": "Access token validation failed",
    }


def test_entra_mcp_auth_fails_closed_for_unmapped_role():
    provider = ContextVarActorProvider()
    app = EntraMCPAuthMiddleware(
        _app(provider),
        token_validator=FakeValidator({"oid": "foundry-agent-456", "roles": ["Unmapped.Role"]}),
        claims_mapper=EntraClaimsMapper(
            role_map={"CEPIO.Agent.Recommender": "ai_agent_recommender"}
        ),
        actor_provider=provider,
    )

    with TestClient(app) as client:
        response = client.get("/", headers={"Authorization": "Bearer token-2"})

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_host_config_helpers_parse_and_fail_closed(monkeypatch):
    monkeypatch.setenv("CEPIO_TEST_MAP", '{"External.Role":"cepio_role"}')
    assert host._json_map("CEPIO_TEST_MAP") == {"External.Role": "cepio_role"}

    monkeypatch.delenv("CEPIO_TEST_MAP")
    assert host._json_map("CEPIO_TEST_MAP") == {}
    with pytest.raises(RuntimeError, match="CEPIO_TEST_MAP is required"):
        host._json_map("CEPIO_TEST_MAP", required=True)

    monkeypatch.setenv("CEPIO_TEST_MAP", "not-json")
    with pytest.raises(RuntimeError, match="must be valid JSON"):
        host._json_map("CEPIO_TEST_MAP")

    monkeypatch.setenv("CEPIO_TEST_MAP", '["not", "a", "map"]')
    with pytest.raises(RuntimeError, match="must be a JSON object mapping strings to strings"):
        host._json_map("CEPIO_TEST_MAP")

    monkeypatch.setenv("CEPIO_TEST_CSV", " alpha, beta ,,gamma ")
    assert host._csv("CEPIO_TEST_CSV") == ["alpha", "beta", "gamma"]
    monkeypatch.delenv("CEPIO_TEST_CSV")
    assert host._csv("CEPIO_TEST_CSV") == []
    with pytest.raises(RuntimeError, match="CEPIO_TEST_CSV is required"):
        host._csv("CEPIO_TEST_CSV", required=True)


def test_create_foundry_mcp_app_with_explicit_components():
    app = host.create_foundry_mcp_app(
        build_runtime(),
        token_validator=FakeValidator(
            {"oid": "agent-1", "roles": ["CEPIO.Agent.Recommender"]}
        ),
        role_map={"CEPIO.Agent.Recommender": "ai_agent_recommender"},
        group_role_map={},
        allowed_hosts=["testserver"],
        allowed_origins=["https://foundry.example"],
        tool_profile="recommendation-only",
    )

    assert isinstance(app, EntraMCPAuthMiddleware)


def test_create_foundry_mcp_app_reads_environment_profile(monkeypatch):
    monkeypatch.setenv(
        "CEPIO_MCP_ENTRA_ROLE_MAP",
        '{"CEPIO.Agent.Recommender":"ai_agent_recommender"}',
    )
    monkeypatch.setenv("CEPIO_MCP_ENTRA_GROUP_ROLE_MAP", '{"group-1":"operator"}')
    monkeypatch.setenv("CEPIO_MCP_ALLOWED_HOSTS", "mcp.example,mcp.example:*")
    monkeypatch.setenv("CEPIO_MCP_ALLOWED_ORIGINS", "https://foundry.example")
    monkeypatch.setenv("CEPIO_MCP_TOOL_PROFILE", "full")

    app = host.create_foundry_mcp_app(
        build_runtime(),
        token_validator=FakeValidator(
            {"oid": "agent-1", "roles": ["CEPIO.Agent.Recommender"]}
        ),
    )

    assert isinstance(app, EntraMCPAuthMiddleware)


def test_create_foundry_mcp_app_rejects_unknown_environment_profile(monkeypatch):
    monkeypatch.setenv(
        "CEPIO_MCP_ENTRA_ROLE_MAP",
        '{"CEPIO.Agent.Recommender":"ai_agent_recommender"}',
    )
    monkeypatch.setenv("CEPIO_MCP_ALLOWED_HOSTS", "mcp.example")
    monkeypatch.setenv("CEPIO_MCP_TOOL_PROFILE", "autonomous")

    with pytest.raises(RuntimeError, match="Unsupported CEPIO_MCP_TOOL_PROFILE"):
        host.create_foundry_mcp_app(
            build_runtime(),
            token_validator=FakeValidator(
                {"oid": "agent-1", "roles": ["CEPIO.Agent.Recommender"]}
            ),
        )


def test_main_uses_safe_default_bind_and_configured_port(monkeypatch):
    sentinel = object()
    called = {}
    monkeypatch.setattr(host, "create_foundry_mcp_app", lambda: sentinel)
    monkeypatch.setattr(
        host.uvicorn,
        "run",
        lambda app, *, host, port: called.update(app=app, host=host, port=port),
    )
    monkeypatch.delenv("CEPIO_MCP_BIND_HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("CEPIO_MCP_PORT", "8123")

    host.main()

    assert called == {"app": sentinel, "host": "127.0.0.1", "port": 8123}
