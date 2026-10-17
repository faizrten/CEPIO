from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

import cepio.api as api_module
from cepio.bootstrap import build_runtime
from cepio.model import OntologyObject, ObjectRef, Relationship


def _rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _configure_entra(monkeypatch, public_key):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")
    monkeypatch.setenv("CEPIO_ENTRA_TENANT_ID", "tenant-test")
    monkeypatch.setenv("CEPIO_ENTRA_AUDIENCE", "api://cepio-test")
    monkeypatch.setenv("CEPIO_ENTRA_ISSUER", "https://issuer.example/tenant-test/v2.0")
    monkeypatch.setenv("CEPIO_ENTRA_JWKS_URI", "https://issuer.example/keys")
    monkeypatch.setattr(
        jwt.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, token: SimpleNamespace(key=public_key),
    )


def _token(private_key, *, roles, audience="api://cepio-test", actor="actor-1"):
    now = datetime.now(timezone.utc)
    claims = {
        "oid": actor,
        "sub": actor,
        "tid": "tenant-test",
        "roles": list(roles),
        "aud": audience,
        "iss": "https://issuer.example/tenant-test/v2.0",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(claims, private_key, algorithm="RS256")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_non_health_route_requires_token(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "entra")
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app)

    assert client.get("/health").status_code == 200
    response = client.get("/objects")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


def test_wrong_audience_is_401(monkeypatch):
    private_key, public_key = _rsa_keys()
    _configure_entra(monkeypatch, public_key)
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app)

    response = client.get(
        "/objects",
        headers=_bearer(_token(private_key, roles={"operator"}, audience="api://wrong")),
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


def test_action_role_spoof_is_rejected_and_audited(monkeypatch):
    private_key, public_key = _rsa_keys()
    _configure_entra(monkeypatch, public_key)
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(
        OntologyObject(
            id="K-SPOOF",
            type="Compressor",
            name="Spoof target",
            interfaces={"MaintainableAsset", "Inspectable", "RiskBearing"},
        )
    )
    client = TestClient(api_module.app)

    response = client.post(
        "/actions",
        headers=_bearer(_token(private_key, roles={"ai_agent_recommender"}, actor="agent-1")),
        json={
            "action_type": "CreateWorkOrder",
            "target": {"id": "K-SPOOF", "type": "Compressor"},
            "actor_id": "agent-1",
            "actor_roles": ["maintenance_manager"],
            "parameters": {},
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "identity_spoof"
    audits = api_module.runtime.all_audits()
    assert len(audits) == 1
    assert audits[0].status.value == "rejected"
    assert audits[0].actor_id == "agent-1"


def test_valid_human_approver_executes_with_token_roles(monkeypatch):
    private_key, public_key = _rsa_keys()
    _configure_entra(monkeypatch, public_key)
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(
        OntologyObject(
            id="WO-APPROVE",
            type="WorkOrder",
            name="Deferred maintenance",
            properties={"status": "open"},
        )
    )
    client = TestClient(api_module.app)

    response = client.post(
        "/actions",
        headers=_bearer(_token(private_key, roles={"maintenance_manager"}, actor="manager-1")),
        json={
            "action_type": "ApproveMaintenanceDeferral",
            "target": {"id": "WO-APPROVE", "type": "WorkOrder"},
            "parameters": {"reason": "planned outage", "until": "2026-11-01"},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "executed"
    assert api_module.runtime.all_audits()[-1].actor_id == "manager-1"


def test_dev_identity_cannot_be_enabled_in_production(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    client = TestClient(api_module.app, raise_server_exceptions=False)
    assert client.get("/objects").status_code == 500


def test_read_policy_filters_properties_before_query_pagination_and_neighbors(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(
        OntologyObject(
            id="K-READ",
            type="Compressor",
            name="Restricted compressor",
            properties={
                "criticality": "high",
                "operatingState": "running",
                "secretProperty": "classified",
            },
            interfaces={"MaintainableAsset"},
        )
    )
    api_module.runtime.upsert_object(
        OntologyObject(
            id="WO-READ",
            type="WorkOrder",
            name="Visible work order",
            properties={"status": "open", "priority": "high", "secretCost": 999999},
        )
    )
    api_module.runtime.add_relationship(
        Relationship(
            type="hasWorkOrder",
            source=ObjectRef(id="K-READ", type="Compressor"),
            target=ObjectRef(id="WO-READ", type="WorkOrder"),
        )
    )
    client = TestClient(api_module.app)
    headers = {
        "X-CEPIO-Dev-Actor": "agent-reader",
        "X-CEPIO-Dev-Roles": "ai_agent_recommender",
    }

    obj = client.get("/objects/K-READ", headers=headers)
    assert obj.status_code == 200
    assert obj.json()["properties"] == {"criticality": "high", "operatingState": "running"}

    hidden_predicate = client.post(
        "/query/objects",
        headers=headers,
        json={
            "object_type": "Equipment",
            "predicates": [{"property": "secretProperty", "operator": "eq", "value": "classified"}],
            "limit": 10,
        },
    )
    assert hidden_predicate.status_code == 200
    assert hidden_predicate.json()["total"] == 0

    visible_query = client.post(
        "/query/objects",
        headers=headers,
        json={"object_type": "Equipment", "limit": 10},
    )
    assert visible_query.status_code == 200
    assert visible_query.json()["total"] == 1
    assert "secretProperty" not in visible_query.json()["items"][0]["properties"]

    neighbors = client.get("/objects/K-READ/neighbors", headers=headers)
    assert neighbors.status_code == 200
    assert neighbors.json()[0]["properties"] == {"status": "open", "priority": "high"}


def test_reverse_neighbor_traversal_is_authorized_and_filtered(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(OntologyObject(id="K-REV", type="Compressor", name="Compressor"))
    api_module.runtime.upsert_object(OntologyObject(id="FEV-REV", type="FailureEvent", name="Failure event"))
    api_module.runtime.add_relationship(
        Relationship(
            type="failureOfEquipment",
            source=ObjectRef(id="FEV-REV", type="FailureEvent"),
            target=ObjectRef(id="K-REV", type="Compressor"),
        )
    )
    client = TestClient(api_module.app)
    headers = {
        "X-CEPIO-Dev-Actor": "agent-reader",
        "X-CEPIO-Dev-Roles": "ai_agent_recommender",
    }

    response = client.get(
        "/objects/K-REV/neighbors?relationship_type=failureOfEquipment&direction=in",
        headers=headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["FEV-REV"]


def test_typed_decision_proposal_requires_named_permission(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(OntologyObject(id="K-DEC", type="Compressor", name="Compressor"))
    client = TestClient(api_module.app)
    body = {
        "decision_type": "maintenance-intervention-recommendation",
        "subject": {"id": "K-DEC", "type": "Compressor"},
        "problem": "Increasing vibration",
        "observations": ["Condition trend increased"],
        "recommendation": "Create a work order",
        "recommended_action": "CreateWorkOrder",
        "confidence": 0.8,
    }

    allowed = client.post(
        "/decisions",
        headers={
            "X-CEPIO-Dev-Actor": "agent-decider",
            "X-CEPIO-Dev-Roles": "ai_agent_recommender",
        },
        json=body,
    )
    assert allowed.status_code == 200
    assert allowed.json()["created_by"] == "agent-decider"

    denied = client.post(
        "/decisions",
        headers={"X-CEPIO-Dev-Actor": "audit-1", "X-CEPIO-Dev-Roles": "auditor"},
        json=body,
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "forbidden"
