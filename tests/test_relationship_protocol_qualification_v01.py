"""Offline signed-token REST/MCP conformance. No production route is installed."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
import json

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.auth import ActorContext, get_actor_context
from cepio.integrations.microsoft.foundry_gateway import (
    ActorContext as MCPActor,
    ContextVarActorProvider,
)
from cepio.integrations.microsoft.hosted_mcp import MCPActorBindingMiddleware
from cepio.relationship_qualification import (
    RelationshipQualificationBoundary,
    RelationshipQualificationUnavailable,
)
from cepio.relationship_query import RelationshipPageQuery
from cepio.runtime import AuthorizationError
from test_relationship_query_v01 import world as world
from test_relationship_source_access_v01 import sources as sources


@pytest.fixture
def protocols(sources, world, monkeypatch):
    repo, adapter, _, state, obj, rel = sources
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()
    for key, value in {
        "CEPIO_ENVIRONMENT": "production",
        "CEPIO_AUTH_MODE": "entra",
        "CEPIO_ENTRA_TENANT_ID": "tenant-a",
        "CEPIO_ENTRA_AUDIENCE": "api://query-offline",
        "CEPIO_ENTRA_ISSUER": "https://issuer.test/tenant-a/v2.0",
        "CEPIO_ENTRA_JWKS_URI": "https://issuer.test/keys",
        "CEPIO_GROUP_ROLE_MAP": "{}",
    }.items():
        monkeypatch.setenv(key, value)
    # Only network key discovery is replaced. JWT signature/algorithm, issuer,
    # audience, time and configured tenant validation use production auth code.
    monkeypatch.setattr(
        jwt.PyJWKClient, "get_signing_key_from_jwt", lambda self, token: SimpleNamespace(key=public)
    )
    provider = ContextVarActorProvider()

    def identity():
        actor = provider.current_actor()
        return ExecutionContext(
            actor_id=actor.subject_id, actor_roles=frozenset(actor.roles), tenant_id=actor.tenant_id
        )

    def rights(context):
        if (
            context.actor_id not in {"host-user", "other-user"}
            or "reader" not in context.actor_roles
        ):
            raise AuthorizationError("Synthetic host authority denied")
        return state["access"].model_copy(update={"actor_id": context.actor_id})

    boundary = RelationshipQualificationBoundary(
        CEPIOApplicationService(world[0]), adapter, identity, lambda _: state["grants"], rights
    )
    rest = FastAPI()

    @rest.post("/qualification/relationships/query")
    def read(query: RelationshipPageQuery, actor: ActorContext = Depends(get_actor_context)):
        with provider.bind(
            MCPActor(
                subject_id=actor.actor_id,
                roles=actor.roles,
                tenant_id=actor.tenant_id,
                auth_mode="oauth2",
            )
        ):
            try:
                return boundary.read(query).model_dump(mode="json")
            except RelationshipQualificationUnavailable:
                raise HTTPException(
                    503,
                    detail={
                        "code": "relationship_query_unavailable",
                        "message": "Relationship query unavailable",
                    },
                ) from None

    server = MCPServer("Offline relationship qualification")

    @server.tool(name="cepio_query_relationships")
    def query_relationships(query: RelationshipPageQuery) -> dict[str, Any]:
        return boundary.read(query).model_dump(mode="json")

    @asynccontextmanager
    async def lifespan(_app):
        async with server.session_manager.run():
            yield

    mcp = FastAPI(lifespan=lifespan)
    mcp.mount(
        "/",
        MCPActorBindingMiddleware(
            server.streamable_http_app(
                streamable_http_path="/mcp",
                stateless_http=True,
                json_response=True,
                transport_security=TransportSecuritySettings(
                    enable_dns_rebinding_protection=True,
                    allowed_hosts=["testserver"],
                    allowed_origins=["https://studio.test"],
                ),
            ),
            provider,
        ),
    )

    def token(**updates):
        now = datetime.now(timezone.utc)
        claims = {
            "oid": "host-user",
            "sub": "host-user",
            "tid": "tenant-a",
            "roles": ["reader"],
            "aud": "api://query-offline",
            "iss": "https://issuer.test/tenant-a/v2.0",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "scp": "query.read",
        }
        claims.update(updates)
        return jwt.encode(claims, private, algorithm="RS256")

    with TestClient(rest) as http, TestClient(mcp) as mc:
        yield SimpleNamespace(
            http=http,
            mcp=mc,
            token=token,
            boundary=boundary,
            provider=provider,
            state=state,
            adapter=adapter,
            repo=repo,
            obj=obj,
            rel=rel,
        )


def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-03-26",
    }


def call(p, query, token=None):
    return p.mcp.post(
        "/mcp",
        headers=headers(token or p.token()),
        json={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "cepio_query_relationships", "arguments": {"query": query}},
        },
    )


def test_signed_rest_mcp_projection_and_cross_protocol_pagination(protocols):
    p = protocols
    initialized = p.mcp.post(
        "/mcp",
        headers=headers(p.token()),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "offline-qualification", "version": "1"},
            },
        },
    )
    assert initialized.status_code == 200 and initialized.json()["result"]["protocolVersion"]
    listed = p.mcp.post(
        "/mcp",
        headers=headers(p.token()),
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ).json()["result"]
    schema = listed["tools"][0]["inputSchema"]
    assert "actor_id" not in json.dumps(schema) and "tenant_id" not in json.dumps(schema)
    query = {"asset_id": "asset", "limit": 1}
    first = p.http.post(
        "/qualification/relationships/query", headers=headers(p.token()), json=query
    )
    assert first.status_code == 200
    page = first.json()
    assert page["subject"]["properties"] == {"status": "candidate"}
    assert page["next_cursor"]
    second = call(p, {**query, "cursor": page["next_cursor"]}).json()["result"]
    assert not second.get("isError", False)
    assert second["structuredContent"]["next_cursor"] is None
    assert "secret" not in json.dumps(second) and "source-" not in json.dumps(second)
    assert p.repo.events_for("asset") == [] and p.repo.all_audits() == []
    with pytest.raises(AuthorizationError):
        p.provider.current_actor()


@pytest.mark.parametrize(
    "updates",
    [
        {"aud": "api://wrong"},
        {"iss": "https://wrong.test"},
        {"tid": "tenant-b"},
        {"exp": datetime(2000, 1, 1, tzinfo=timezone.utc)},
    ],
)
def test_invalid_bearer_claims_denied_by_both_transports(protocols, updates):
    p = protocols
    bearer = p.token(**updates)
    assert (
        p.http.post(
            "/qualification/relationships/query",
            headers=headers(bearer),
            json={"asset_id": "asset"},
        ).status_code
        == 401
    )
    assert call(p, {"asset_id": "asset"}, bearer).status_code == 401


def test_missing_and_bad_signature_tokens_cannot_use_dev_header_identity(protocols):
    p = protocols
    spoof = {"X-CEPIO-Dev-Actor": "host-user", "X-CEPIO-Dev-Roles": "reader"}
    assert (
        p.http.post(
            "/qualification/relationships/query", headers=spoof, json={"asset_id": "asset"}
        ).status_code
        == 401
    )
    assert p.mcp.post("/mcp", headers=spoof, json={}).status_code == 401
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = jwt.decode(p.token(), options={"verify_signature": False})
    bad = jwt.encode(claims, other, algorithm="RS256")
    assert call(p, {"asset_id": "asset"}, bad).status_code == 401
    assert (
        p.http.post(
            "/qualification/relationships/query", headers=headers(bad), json={"asset_id": "asset"}
        ).status_code
        == 401
    )


def test_signed_roleless_identity_denied_but_verified_group_mapping_is_honored(
    protocols, monkeypatch
):
    p = protocols
    roleless = p.token(roles=[])
    assert call(p, {"asset_id": "asset"}, roleless).status_code == 403
    assert (
        p.http.post(
            "/qualification/relationships/query",
            headers=headers(roleless),
            json={"asset_id": "asset"},
        ).status_code
        == 503
    )
    monkeypatch.setenv("CEPIO_GROUP_ROLE_MAP", json.dumps({"synthetic-reader-group": ["reader"]}))
    grouped = p.token(roles=[], groups=["synthetic-reader-group"])
    assert (
        p.http.post(
            "/qualification/relationships/query",
            headers=headers(grouped),
            json={"asset_id": "asset"},
        ).status_code
        == 200
    )
    assert not call(p, {"asset_id": "asset"}, grouped).json()["result"].get("isError", False)


def test_qualification_transports_have_no_operational_write_tool_or_path(protocols):
    p = protocols
    response = p.mcp.post(
        "/mcp",
        headers=headers(p.token()),
        json={
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": "cepio_execute_action", "arguments": {}},
        },
    )
    assert response.json()["result"]["isError"] is True
    assert (
        p.http.post("/qualification/actions", headers=headers(p.token()), json={}).status_code
        == 404
    )
    assert p.repo.all_audits() == []


@pytest.mark.parametrize(
    "extra",
    [
        {"actor_id": "admin"},
        {"tenant_id": "tenant-b"},
        {"source_ids": ["source-edge"]},
        {"limit": 5000},
    ],
)
def test_payload_cannot_override_host_authority_or_bounds(protocols, extra):
    p = protocols
    payload = {"asset_id": "asset", **extra}
    assert (
        p.http.post(
            "/qualification/relationships/query", headers=headers(p.token()), json=payload
        ).status_code
        == 422
    )
    result = call(p, payload).json()["result"]
    assert result["isError"] is True


def test_cross_actor_cursor_replay_and_source_revocation_fail_closed(protocols):
    p = protocols
    query = {"asset_id": "asset", "limit": 1}
    first = p.http.post(
        "/qualification/relationships/query", headers=headers(p.token()), json=query
    ).json()
    replay = {**query, "cursor": first["next_cursor"]}
    assert call(p, replay, p.token(oid="other-user")).json()["result"]["isError"]
    p.state["access"] = p.state["access"].model_copy(
        update={"rights_version": "revoked-v2", "source_ids": frozenset()}
    )
    denied = p.http.post(
        "/qualification/relationships/query", headers=headers(p.token()), json=replay
    )
    assert denied.status_code == 503
    assert denied.json() == {
        "detail": {
            "code": "relationship_query_unavailable",
            "message": "Relationship query unavailable",
        }
    }
    assert "source-" not in json.dumps(call(p, replay).json())


def test_denied_and_missing_subjects_have_identical_boundary_errors(protocols):
    p = protocols
    missing = p.http.post(
        "/qualification/relationships/query",
        headers=headers(p.token()),
        json={"asset_id": "missing"},
    )
    denied = p.http.post(
        "/qualification/relationships/query",
        headers=headers(p.token(oid="intruder")),
        json={"asset_id": "asset"},
    )
    assert missing.status_code == denied.status_code == 503 and missing.json() == denied.json()


def test_concurrent_actor_contexts_and_cursor_ownership_are_isolated(protocols):
    p = protocols

    def invoke(actor):
        response = p.http.post(
            "/qualification/relationships/query",
            headers=headers(p.token(oid=actor)),
            json={"asset_id": "asset", "limit": 1},
        )
        return actor, response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, ["host-user", "other-user"]))
    assert all(status == 200 for _, status, _ in results)
    for actor, _, page in results:
        other = "other-user" if actor == "host-user" else "host-user"
        assert call(
            p, {"asset_id": "asset", "limit": 1, "cursor": page["next_cursor"]}, p.token(oid=other)
        ).json()["result"]["isError"]
    with pytest.raises(AuthorizationError):
        p.provider.current_actor()


@pytest.fixture
def unit(sources, world):
    repo, adapter, _, state, _, _ = sources

    def rights(context):
        return state["access"].model_copy(update={"actor_id": context.actor_id})

    boundary = RelationshipQualificationBoundary(
        CEPIOApplicationService(world[0]),
        adapter,
        lambda: state["identity"],
        lambda _: state["grants"],
        rights,
    )
    return boundary, state, repo


def test_per_actor_and_global_admission_limits_bound_memory_and_reset(unit, monkeypatch):
    boundary, state, _ = unit
    query = {"asset_id": "asset"}
    # The admission-window regression must not depend on CI/coverage runtime speed.
    # Other tests independently exercise real SQLite and VM/elapsed-time limits.
    import cepio.relationship_qualification as module

    clock = [boundary._window]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    for _ in range(30):
        boundary.read(query)
    with pytest.raises(RelationshipQualificationUnavailable):
        boundary.read(query)
    for n in range(3):
        state["identity"] = state["identity"].model_copy(update={"actor_id": f"actor-{n}"})
        for _ in range(30):
            boundary.read(query)
    assert boundary._total == 120 and len(boundary._counts) == 4
    state["identity"] = state["identity"].model_copy(update={"actor_id": "new-actor"})
    with pytest.raises(RelationshipQualificationUnavailable):
        boundary.read(query)
    assert len(boundary._counts) == 4
    clock[0] = boundary._window + 61
    assert boundary.read(query).links
    assert boundary._total == 1 and len(boundary._counts) == 1


def test_concurrency_saturation_and_resolver_errors_are_uniform_and_release_slots(unit):
    boundary, _, _ = unit
    for _ in range(4):
        assert boundary._slots.acquire(blocking=False)
    with pytest.raises(RelationshipQualificationUnavailable) as busy:
        boundary.read({"asset_id": "asset"})
    for _ in range(4):
        boundary._slots.release()

    def failing():
        raise RuntimeError("secret-source-identity")

    boundary._identity = failing
    with pytest.raises(RelationshipQualificationUnavailable) as denied:
        boundary.read({"asset_id": "asset"})
    assert str(busy.value) == str(denied.value) == "Relationship query unavailable"
    assert denied.value.__suppress_context__
    assert boundary._slots.acquire(blocking=False)
    boundary._slots.release()


@pytest.mark.parametrize(
    "changes",
    [
        {"actor_id": ""},
        {"tenant_id": None},
        {"actor_roles": frozenset()},
        {"actor_id": "x" * 513},
        {"tenant_id": "x" * 513},
        {"actor_roles": frozenset(str(n) for n in range(33))},
        {"actor_roles": frozenset({"r" * 129})},
    ],
)
def test_missing_or_oversized_host_identity_fails_closed(unit, changes):
    boundary, state, _ = unit
    state["identity"] = state["identity"].model_copy(update=changes)
    with pytest.raises(RelationshipQualificationUnavailable):
        boundary.read({"asset_id": "asset"})
    assert boundary._counts == {}


def test_source_unaware_mode_and_forged_query_models_not_admitted(unit, sources, world):
    _, adapter, _, _, _, _ = sources
    with pytest.raises(ValueError):
        RelationshipQualificationBoundary(
            CEPIOApplicationService(world[0]), adapter, lambda: None, lambda _: None, None
        )
    boundary, _, repo = unit
    before = repo._conn.total_changes
    with pytest.raises(RelationshipQualificationUnavailable):
        boundary.read(RelationshipPageQuery(asset_id="asset").model_copy(update={"limit": 5000}))
    assert boundary.read({"asset_id": "asset"}).links
    assert repo._conn.total_changes == before


def test_database_budget_and_missing_request_context_are_uniform(unit, monkeypatch):
    boundary, _, _ = unit
    import cepio.relationship_query as query_module

    monkeypatch.setattr(
        query_module,
        "_PAGE_SQL",
        "WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT * FROM n",
    )
    with pytest.raises(RelationshipQualificationUnavailable) as exhausted:
        boundary.read({"asset_id": "asset"})
    assert str(exhausted.value) == "Relationship query unavailable"
    with pytest.raises(LookupError):
        boundary._context.get()
    boundary._identity = lambda: None
    with pytest.raises(RelationshipQualificationUnavailable):
        boundary.read({"asset_id": "asset"})


def test_single_captured_identity_cannot_change_mid_read(unit):
    boundary, state, _ = unit
    calls = []

    def identity():
        calls.append(1)
        return state["identity"]

    def resolver(context):
        state["identity"] = state["identity"].model_copy(update={"actor_id": "other-user"})
        return state["access"].model_copy(update={"actor_id": context.actor_id})

    boundary._identity = identity
    boundary._reader.configure_source_access(resolver)
    assert boundary.read({"asset_id": "asset"}).links
    assert len(calls) == 1


def test_unqualified_reader_not_exposed_by_default_rest_or_mcp_builders():
    from pathlib import Path
    from cepio.public_api import app

    contract = app.openapi()
    assert "/qualification/relationships/query" not in contract["paths"]
    assert "/api/v1/relationships/query" not in contract["paths"]
    assert "RelationshipPageQuery" not in contract["components"]["schemas"]
    root = Path(__file__).resolve().parents[1]
    for path in (
        "src/cepio/host_api.py",
        "src/cepio/public_api.py",
        "src/cepio/integrations/microsoft/foundry_mcp.py",
    ):
        assert "relationship_qualification" not in (root / path).read_text(encoding="utf-8")
        assert "cepio_query_relationships" not in (root / path).read_text(encoding="utf-8")
