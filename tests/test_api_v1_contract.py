from fastapi.testclient import TestClient
import pytest

import cepio.api as legacy_api
import cepio.public_api as public_api
from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.model import OntologyObject


def _dev_headers(*roles: str, actor: str = "test-user") -> dict[str, str]:
    return {
        "X-CEPIO-Dev-Actor": actor,
        "X-CEPIO-Dev-Roles": ",".join(roles),
    }


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


def test_operation_ids_are_stable_for_sdk_generation():
    public_api.app.openapi_schema = None
    schema = public_api.app.openapi()
    assert schema["paths"]["/api/v1/objects/{object_id}"]["get"]["operationId"] == "getObject"
    assert schema["paths"]["/api/v1/query/objects"]["post"]["operationId"] == "queryObjects"
    assert schema["paths"]["/api/v1/actions"]["post"]["operationId"] == "executeAction"
