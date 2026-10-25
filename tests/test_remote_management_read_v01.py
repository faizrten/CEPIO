from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.config import RuntimeSettings
from cepio.management_remote import build_remote_management_router
from cepio.management_runtime import build_management_service


EXPECTED_PATHS = {
    "/management/v1/health",
    "/management/v1/status",
    "/management/v1/capabilities",
    "/management/v1/skills",
    "/management/v1/industry-iq",
    "/management/v1/bindings",
    "/management/v1/profiles",
    "/management/v1/investigations",
}


def remote_app() -> FastAPI:
    runtime = build_runtime()
    settings = RuntimeSettings(
        environment="test",
        db_url="memory://",
        resource_root=None,
        ontology_dir=None,
        profiles=(),
        validate_types=True,
        validate_properties=True,
        strict_properties=False,
    )
    auth = AuthSettings(
        mode="dev",
        environment="test",
        tenant_id=None,
        audience=None,
        issuer=None,
        jwks_uri=None,
        group_role_map={},
    )
    service = build_management_service(
        runtime,
        runtime_settings=settings,
        auth_settings=auth,
    )
    app = FastAPI()
    app.include_router(build_remote_management_router(service))
    return app


def test_remote_management_requires_explicit_reader_role(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    client = TestClient(remote_app(), client=("203.0.113.10", 50000))

    unauthorised = client.get("/management/v1/health")
    assert unauthorised.status_code == 403
    assert unauthorised.json()["detail"]["code"] == "management_forbidden"

    authorised = client.get(
        "/management/v1/health",
        headers={"X-CEPIO-Dev-Roles": "cepio_management_reader"},
    )
    assert authorised.status_code == 200


def test_remote_management_reader_can_read_every_management_descriptor(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    client = TestClient(remote_app(), client=("203.0.113.10", 50000))
    headers = {"X-CEPIO-Dev-Roles": "cepio_management_reader"}

    for path in EXPECTED_PATHS:
        assert client.get(path, headers=headers).status_code == 200


def test_remote_management_admin_retains_read_access(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    client = TestClient(remote_app())

    response = client.get(
        "/management/v1/status",
        headers={"X-CEPIO-Dev-Roles": "cepio_admin"},
    )
    assert response.status_code == 200


def test_remote_management_projection_is_get_only(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    app = remote_app()
    client = TestClient(app)
    headers = {"X-CEPIO-Dev-Roles": "cepio_management_reader"}

    assert client.post("/management/v1/status", headers=headers).status_code == 405
    assert client.put("/management/v1/bindings", headers=headers).status_code == 405
    assert client.delete("/management/v1/profiles", headers=headers).status_code == 405

    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi) == EXPECTED_PATHS
    assert all(set(openapi[path]) == {"get"} for path in EXPECTED_PATHS)


def test_host_composition_exposes_public_and_remote_management_contracts(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    from cepio.host_api import app

    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200
    # Remote Management metadata must never describe an authenticated remote host as loopback-only.
    # Unauthenticated management access remains denied.
    assert client.get("/management/v1/health").status_code == 403
    response = client.get(
        "/management/v1/health",
        headers={"X-CEPIO-Dev-Roles": "cepio_management_reader"},
    )
    assert response.status_code == 200
    assert response.json()["local_only"] is False
    assert response.json()["scope"] == "process-only"
