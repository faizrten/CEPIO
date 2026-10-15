import json

import httpx

from cepio.model import ActionRequest, ObjectRef, OntologyObject
from cepio.sdk import CEPIOClient


def test_python_sdk_uses_v1_and_bearer_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["authorization"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            headers={"ETag": '"3"'},
            json={
                "id": "K-201",
                "type": "Compressor",
                "name": "K-201",
                "properties": {},
                "interfaces": [],
                "version": 3,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        )

    client = CEPIOClient(
        "https://cepio.example",
        access_token="token-value",
        transport=httpx.MockTransport(handler),
    )
    obj, etag = client.get_object_with_etag("K-201")
    client.close()

    assert obj.id == "K-201"
    assert etag == '"3"'
    assert seen == {
        "path": "/api/v1/objects/K-201",
        "authorization": "Bearer token-value",
    }


def test_upsert_uses_if_match_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["if_match"] = request.headers.get("If-Match")
        payload = json.loads(request.content)
        payload["version"] = 4
        return httpx.Response(200, json=payload)

    client = CEPIOClient(
        "https://cepio.example",
        dev_actor="developer",
        dev_roles={"cepio_admin"},
        transport=httpx.MockTransport(handler),
    )
    stored = client.upsert_object(
        OntologyObject(id="K-201", type="Compressor", name="K-201", version=3),
        expected_version=3,
    )
    client.close()

    assert stored.version == 4
    assert seen["path"] == "/api/v1/objects/K-201"
    assert seen["if_match"] == '"3"'


def test_action_client_does_not_send_actor_authority():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["idempotency"] = request.headers.get("Idempotency-Key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "action_id": "action-1",
                "action_type": "CreateWorkOrder",
                "target": {"id": "K-201", "type": "Compressor"},
                "status": "executed",
                "message": "Action executed",
                "effects": {},
                "executed_at": "2026-01-01T00:00:00Z",
                "audit_id": "audit-1",
                "replayed": False,
                "policy_reasons": [],
                "compensation": None,
            },
        )

    client = CEPIOClient(
        "https://cepio.example",
        access_token="token-value",
        transport=httpx.MockTransport(handler),
    )
    request = ActionRequest(
        action_type="CreateWorkOrder",
        target=ObjectRef(id="K-201", type="Compressor"),
        actor_id="must-not-be-sent",
        actor_roles={"cepio_admin"},
        parameters={"priority": "high"},
        idempotency_key="work-order-1",
    )
    result = client.execute_action(request)
    client.close()

    assert result.status.value == "executed"
    assert seen["path"] == "/api/v1/actions"
    assert seen["idempotency"] == "work-order-1"
    assert "actor_id" not in seen["body"]
    assert "actor_roles" not in seen["body"]
