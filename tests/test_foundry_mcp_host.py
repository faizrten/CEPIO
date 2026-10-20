from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from cepio.auth import ActorContext as AuthActorContext
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


def _app(provider: ContextVarActorProvider):
    async def downstream(scope, receive, send):
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
