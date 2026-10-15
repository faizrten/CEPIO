from fastapi.testclient import TestClient

import cepio.api as api_module
from cepio.bootstrap import build_runtime
from cepio.model import OntologyObject


def test_openapi_only_exposes_versioned_public_routes():
    paths = api_module.app.openapi()["paths"]
    assert paths
    assert all(path.startswith("/api/v1/") for path in paths)
    assert "/api/v1/objects" in paths
    assert "/api/v1/query/objects" in paths
    assert "/api/v1/actions" in paths


def test_legacy_and_v1_routes_share_runtime_semantics():
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(
        OntologyObject(id="K-V1", type="Compressor", name="V1 Compressor")
    )
    client = TestClient(api_module.app)

    legacy = client.get("/objects/K-V1")
    versioned = client.get("/api/v1/objects/K-V1")

    assert legacy.status_code == 200
    assert versioned.status_code == 200
    assert versioned.json() == legacy.json()


def test_operation_ids_are_stable_for_sdk_generation():
    schema = api_module.app.openapi()
    assert schema["paths"]["/api/v1/objects/{object_id}"]["get"]["operationId"] == "getObject"
    assert schema["paths"]["/api/v1/query/objects"]["post"]["operationId"] == "queryObjects"
    assert schema["paths"]["/api/v1/actions"]["post"]["operationId"] == "executeAction"
