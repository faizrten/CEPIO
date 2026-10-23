"""Offline signed-token matrix; real validation, isolated test JWKS key only."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from cepio.host_api import app


@pytest.fixture
def signed_host(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for name, value in {
        "CEPIO_ENVIRONMENT": "production",
        "CEPIO_AUTH_MODE": "entra",
        "CEPIO_ENTRA_TENANT_ID": "tenant-test",
        "CEPIO_ENTRA_AUDIENCE": "api://cepio-test",
        "CEPIO_ENTRA_ISSUER": "https://issuer.example/tenant-test/v2.0",
        "CEPIO_ENTRA_JWKS_URI": "https://issuer.example/keys",
        "CEPIO_GROUP_ROLE_MAP": "{}",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        jwt.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, token: SimpleNamespace(key=key.public_key()),
    )

    def token(**changes):
        now = datetime.now(timezone.utc)
        claims = {
            "oid": "reader-test",
            "tid": "tenant-test",
            "aud": "api://cepio-test",
            "iss": "https://issuer.example/tenant-test/v2.0",
            "roles": ["cepio_management_reader"],
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        claims.update(changes)
        return jwt.encode(claims, key, algorithm="RS256")

    with TestClient(app) as client:
        yield client, token


def read_surface(client, surface, token):
    headers = {"Authorization": "Bearer " + token}
    if surface == "mcp":
        headers["Accept"] = "application/json, text/event-stream"
        return client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "offline-auth-matrix", "version": "1"},
                },
            },
        )
    path = "/api/v1/objects" if surface == "rest" else "/management/v1/health"
    return client.get(path, headers=headers)


@pytest.mark.parametrize("surface", ["rest", "management", "mcp"])
@pytest.mark.parametrize(
    "changes",
    [
        {"aud": "api://wrong"},
        {"tid": "wrong-tenant"},
        {"tid": None},
        {"iss": "https://issuer.example/wrong/v2.0"},
    ],
)
def test_signed_identity_mismatch_is_401(signed_host, surface, changes):
    client, token = signed_host
    response = read_surface(client, surface, token(**changes))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    body = response.json()
    assert body.get("detail", body.get("error", body))["code"] == "invalid_token"


@pytest.mark.parametrize("surface", ["rest", "management", "mcp"])
def test_signed_reader_positive_control(signed_host, surface):
    client, token = signed_host
    assert read_surface(client, surface, token()).status_code == 200


@pytest.mark.parametrize("roles", [[], ["unrelated-role"]])
def test_management_requires_approved_role(signed_host, roles):
    client, token = signed_host
    response = read_surface(client, "management", token(roles=roles))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "management_forbidden"


def test_mcp_roleless_identity_is_403(signed_host):
    client, token = signed_host
    response = read_surface(client, "mcp", token(roles=[]))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "mcp_role_required"


@pytest.mark.parametrize("surface", ["rest", "management", "mcp"])
def test_invalid_jwt_key_lookup_is_401(signed_host, monkeypatch, surface):
    client, _ = signed_host

    def reject(self, token):
        raise jwt.DecodeError("Untrusted token header")

    monkeypatch.setattr(jwt.PyJWKClient, "get_signing_key_from_jwt", reject)
    response = read_surface(client, surface, "not-a-jwt")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
