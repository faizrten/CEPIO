from fastapi.testclient import TestClient
import pytest

import cepio.api as legacy_api
import cepio.public_api as public_api
from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.model import OntologyObject


def _dev_headers(*roles: str, actor: str = "test-user", **extra: str) -> dict[str, str]:
    headers = {
        "X-CEPIO-Dev-Actor": actor,
        "X-CEPIO-Dev-Roles": ",".join(roles),
    }
    headers.update(extra)
    return headers


def test_openapi_only_exposes_versioned_public_routes():
    public_api.app.openapi_schema = None
    paths = public_api.app.openapi()["paths"]
    assert paths
    assert all(path.startswith("/api/v1/") for path in paths)
    assert "/api/v1/objects" in paths
    assert "/api/v1/query/objects" in paths
    assert "/api/v1/actions" in paths


def test_legacy_and_v1_routes_share_secured_runtime_semantics(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    runtime = build_runtime()
    legacy_api.runtime = runtime
    runtime.upsert_object(OntologyObject(id="K-V1", type="Compressor", name="V1 Compressor"))
    client = TestClient(public_api.app)
    headers = _dev_headers("cepio_admin")

    legacy = client.get("/objects/K-V1", headers=headers)
    versioned = client.get("/api/v1/objects/K-V1", headers=headers)

    assert legacy.status_code == 200
    assert versioned.status_code == 200
    assert versioned.json() == legacy.json()


def test_v1_dev_identity_is_explicitly_non_production(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    legacy_api.runtime = build_runtime()
    client = TestClient(public_api.app)

    response = client.get("/api/v1/objects")
    assert response.status_code == 200

    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="permitted only"):
        AuthSettings.from_env()


def test_v1_object_etag_and_if_match_round_trip(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    runtime = build_runtime()
    legacy_api.runtime = runtime
    runtime.upsert_object(OntologyObject(id="K-ETAG", type="Compressor", name="Before"))
    client = TestClient(public_api.app)
    headers = _dev_headers("cepio_admin")

    read = client.get("/api/v1/objects/K-ETAG", headers=headers)
    assert read.status_code == 200
    assert read.headers["etag"] == '"1"'

    payload = read.json()
    payload["name"] = "After"
    updated = client.put(
        "/api/v1/objects/K-ETAG",
        headers={**headers, "If-Match": read.headers["etag"]},
        json=payload,
    )
    assert updated.status_code == 200
    assert updated.headers["etag"] == '"2"'

    stale = client.put(
        "/api/v1/objects/K-ETAG",
        headers={**headers, "If-Match": '"1"'},
        json=payload,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "version_conflict"
    assert stale.json()["requestId"]


def test_v1_errors_include_request_id(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    legacy_api.runtime = build_runtime()
    client = TestClient(public_api.app)
    request_id = "test-request-123"

    response = client.get(
        "/api/v1/objects/does-not-exist",
        headers=_dev_headers("cepio_admin", **{"X-Request-ID": request_id}),
    )
    assert response.status_code == 404
    assert response.headers["x-request-id"] == request_id
    assert response.json()["code"] == "not_found"
    assert response.json()["requestId"] == request_id
    assert "message" in response.json()
    assert "details" in response.json()


def test_v1_action_uses_idempotency_header_and_rejects_conflict(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    legacy_api.runtime = build_runtime()
    client = TestClient(public_api.app)
    body = {
        "action_type": "SetOperatingState",
        "target": {"id": "K-1", "type": "Compressor"},
        "parameters": {},
        "idempotency_key": "body-key",
    }

    response = client.post(
        "/api/v1/actions",
        headers=_dev_headers("cepio_admin", **{"Idempotency-Key": "header-key"}),
        json=body,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_conflict"


def test_operation_ids_are_stable_for_sdk_generation():
    public_api.app.openapi_schema = None
    schema = public_api.app.openapi()
    assert schema["paths"]["/api/v1/objects/{object_id}"]["get"]["operationId"] == "getObject"
    assert schema["paths"]["/api/v1/query/objects"]["post"]["operationId"] == "queryObjects"
    assert schema["paths"]["/api/v1/actions"]["post"]["operationId"] == "executeAction"
    params = schema["paths"]["/api/v1/actions"]["post"]["parameters"]
    assert any(param["name"] == "Idempotency-Key" and param["in"] == "header" for param in params)
