from fastapi.testclient import TestClient

import cepio.api as api_module
from cepio.bootstrap import build_runtime


def _dev_headers(*roles: str, actor: str = "test-user") -> dict[str, str]:
    return {
        "X-CEPIO-Dev-Actor": actor,
        "X-CEPIO-Dev-Roles": ",".join(roles),
    }


def test_api_health_and_policy_rejection_are_explicit_and_audited(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app)
    assert client.get("/health").json()["version"] == "0.3.0"

    obj = {
        "id": "K-API",
        "type": "Compressor",
        "name": "API Compressor",
        "properties": {"criticality": "high"},
        "interfaces": ["MaintainableAsset", "Inspectable", "RiskBearing"],
    }
    response = client.put("/objects/K-API", json=obj, headers=_dev_headers("cepio_admin"))
    assert response.status_code == 200

    action = {
        "action_type": "CreateWorkOrder",
        "target": {"id": "K-API", "type": "Compressor"},
        "parameters": {},
    }
    rejected = client.post(
        "/actions",
        json=action,
        headers=_dev_headers("ai_agent_recommender", actor="agent-api"),
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["status"] == "rejected"
    audit = client.get("/audit", headers=_dev_headers("auditor")).json()
    assert len(audit) == 1
    assert audit[0]["status"] == "rejected"


def test_graph_backend_endpoint_is_cpu_safe(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app)

    response = client.get("/graph/backend", headers=_dev_headers("operator"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected"] in {"networkx", "cugraph"}
    assert "cugraph_installed" in payload
