from fastapi.testclient import TestClient

import cepio.api as api_module
from cepio import __version__
from cepio.bootstrap import build_runtime


def test_api_health_and_policy_rejection_are_explicit_and_audited():
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app)
    assert client.get("/health").json()["version"] == __version__

    obj = {
        "id": "K-API",
        "type": "Compressor",
        "name": "API Compressor",
        "properties": {"criticality": "high"},
        "interfaces": ["MaintainableAsset", "Inspectable", "RiskBearing"],
    }
    response = client.put("/objects/K-API", json=obj)
    assert response.status_code == 200

    action = {
        "action_type": "CreateWorkOrder",
        "target": {"id": "K-API", "type": "Compressor"},
        "actor_id": "agent-api",
        "actor_roles": ["ai_agent_recommender"],
        "parameters": {},
    }
    rejected = client.post("/actions", json=action)
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["status"] == "rejected"
    audit = client.get("/audit").json()
    assert len(audit) == 1
    assert audit[0]["status"] == "rejected"


def test_graph_backend_endpoint_is_cpu_safe():
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app)

    response = client.get("/graph/backend")
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected"] in {"networkx", "cugraph"}
    assert "cugraph_installed" in payload
