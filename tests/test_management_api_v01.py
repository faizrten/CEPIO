from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.config import RuntimeSettings
from cepio.management_api import _is_local_host, create_management_app
from cepio.management_runtime import build_management_service_from_registrations
from cepio.platform_bindings import (
    BindingCapability,
    BindingMode,
    BindingRegistration,
    PlatformBindingManifest,
)


def management_service():
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
    return build_management_service_from_registrations(
        runtime,
        runtime_settings=settings,
        auth_settings=auth,
        binding_registrations=[
            BindingRegistration(
                manifest=PlatformBindingManifest(
                    binding_id="synthetic-reference",
                    provider_id="synthetic",
                    source_system="synthetic-reference",
                    mode=BindingMode.evidence,
                    capabilities=frozenset({BindingCapability.resolve_evidence}),
                ),
                capability_id="industrial-observation",
            )
        ],
    )


def test_local_management_api_exposes_only_read_only_management_routes():
    app = create_management_app(management_service())
    client = TestClient(app)

    expected = {
        "/management/v1/health",
        "/management/v1/status",
        "/management/v1/capabilities",
        "/management/v1/skills",
        "/management/v1/industry-iq",
        "/management/v1/bindings",
        "/management/v1/profiles",
    }
    for path in expected:
        response = client.get(path)
        assert response.status_code == 200

    assert client.post("/management/v1/status").status_code == 405
    assert client.get("/api/v1/health").status_code == 404

    paths = set(client.get("/openapi.json").json()["paths"])
    assert paths == expected
    assert all(set(client.get("/openapi.json").json()["paths"][path]) == {"get"} for path in paths)


def test_management_api_payloads_are_durable_descriptors():
    client = TestClient(create_management_app(management_service()))

    status = client.get("/management/v1/status").json()
    skills = client.get("/management/v1/skills").json()
    bindings = client.get("/management/v1/bindings").json()
    capabilities = client.get("/management/v1/capabilities").json()

    assert status["environment"] == "test"
    assert status["persistence_mode"] == "memory"
    assert status["metadata"]["contract_version"] == "0.1.0"
    assert "db_url" not in status
    assert skills[0]["skill_id"] == "cepio.skill.maintenance.assess-maintenance-deferral"
    assert skills[0]["executable"] is True
    assert bindings == [
        {
            "binding_id": "synthetic-reference",
            "provider": "synthetic",
            "capability": "industrial-observation",
            "mode": "read",
            "status": "ready",
            "authority": "observation-only",
            "source_system": "synthetic-reference",
            "declared_capabilities": ["resolve-evidence"],
            "binding_contract_version": "0.1",
        }
    ]
    assert capabilities["binding_contract_version"] == "0.1"


def test_management_api_rejects_non_loopback_clients():
    app = create_management_app(management_service())
    remote = TestClient(app, client=("203.0.113.10", 50000))

    response = remote.get("/management/v1/health")

    assert response.status_code == 403
    assert "loopback" in response.json()["detail"]


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        (None, False),
        ("localhost", True),
        ("testclient", True),
        ("127.0.0.1", True),
        ("::1", True),
        ("203.0.113.10", False),
        ("not-an-ip", False),
    ],
)
def test_local_host_classification(host: str | None, expected: bool):
    assert _is_local_host(host) is expected


def test_management_launcher_binds_loopback(monkeypatch):
    from cepio import management_api

    calls: list[tuple[str, str, int]] = []

    def fake_run(target: str, *, host: str, port: int) -> None:
        calls.append((target, host, port))

    monkeypatch.setenv("CEPIO_MANAGEMENT_PORT", "8123")
    monkeypatch.setattr(management_api.uvicorn, "run", fake_run)

    management_api.main()

    assert calls == [("cepio.management_api:app", "127.0.0.1", 8123)]


def test_management_launcher_rejects_invalid_port(monkeypatch):
    from cepio import management_api

    monkeypatch.setenv("CEPIO_MANAGEMENT_PORT", "70000")
    with pytest.raises(RuntimeError, match="between 1 and 65535"):
        management_api.main()
