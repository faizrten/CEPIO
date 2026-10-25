from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.config import RuntimeSettings
from cepio.industry_iq import IndustryIQDeploymentManifest, IndustryIQPackManifest
from cepio.management_contract import (
    BindingDescriptor,
    BindingVerification,
    CEPIOManagementService,
    InvestigationOperations,
)


def _service(runtime=None, **kwargs):
    return CEPIOManagementService(
        runtime or build_runtime(),
        runtime_settings=RuntimeSettings(
            environment="test",
            db_url="memory://",
            resource_root=None,
            ontology_dir=None,
            profiles=(),
            validate_types=True,
            validate_properties=True,
            strict_properties=False,
        ),
        auth_settings=AuthSettings(
            mode="dev",
            environment="test",
            tenant_id=None,
            audience=None,
            issuer=None,
            jwks_uri=None,
            group_role_map={},
        ),
        **kwargs,
    )


def _binding():
    return BindingDescriptor(
        binding_id="test-historian",
        provider="synthetic",
        capability="resolve-evidence",
        mode="read",
        status="ready",
        authority="observation-only",
    )


def test_registration_is_not_live_readiness():
    manager = _service(bindings=[_binding()])
    assert manager.list_bindings()[0].status == "ready"
    assert manager.list_bindings()[0].verified_readiness == "not-verified"
    assert manager.capabilities().binding_inventory_state == "not-wired"
    assert manager.capabilities().readiness_qualified is False


def test_live_binding_requires_current_scoped_probe():
    now = datetime.now(timezone.utc)
    probe = BindingVerification(
        binding_id="test-historian",
        result="passed",
        checked_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=9),
        evidence_ref="test-probe-123",
    )
    manager = _service(
        bindings=[_binding()],
        binding_inventory_connected=True,
        binding_verifications={"test-historian": probe},
    )
    item = manager.list_bindings()[0]
    assert item.verified_readiness == "verified"
    assert item.verification_ref == "test-probe-123"
    assert manager.capabilities().binding_inventory_state == "connected"

    expired = probe.model_copy(update={"expires_at": now - timedelta(seconds=1)})
    assert (
        _service(bindings=[_binding()], binding_verifications={"test-historian": expired})
        .list_bindings()[0]
        .verified_readiness
        == "stale"
    )
    failed = probe.model_copy(update={"result": "failed"})
    assert (
        _service(bindings=[_binding()], binding_verifications={"test-historian": failed})
        .list_bindings()[0]
        .verified_readiness
        == "failed"
    )
    future = probe.model_copy(update={"checked_at": now + timedelta(days=1)})
    assert (
        _service(bindings=[_binding()], binding_verifications={"test-historian": future})
        .list_bindings()[0]
        .verified_readiness
        == "not-verified"
    )


def test_pack_deployment_manifest_is_version_specific():
    runtime = build_runtime()
    runtime.industry_iq_packs = {"example": "1.2.3"}
    manifest = IndustryIQPackManifest(
        pack_id="example",
        version="1.2.3",
        requires_core=">=0.4.0,<1.0.0",
        functions={"assess"},
    )
    runtime.industry_iq_deployment_manifest = IndustryIQDeploymentManifest(
        core_version="0.4.0",
        packs={"example": manifest},
        install_order=["example"],
    )
    pack = _service(runtime).list_industry_iq()[0]
    assert pack.deployment_recorded is True
    assert pack.functions == ["assess"]
    assert pack.requires_core == ">=0.4.0,<1.0.0"
    runtime.industry_iq_packs["example"] = "1.2.4"
    next_pack = _service(runtime).list_industry_iq()[0]
    assert next_pack.version == "1.2.4"
    assert next_pack.deployment_recorded is False
    assert next_pack.functions == []


def test_investigation_ops_default_avoids_fabricated_counts():
    snapshot = _service().investigation_operations("tenant-a")
    assert snapshot.state == "not-connected"
    assert snapshot.counts is None


def test_investigation_ops_is_tenant_scoped_and_rejects_mismatched_source():
    def observer(tenant):
        return InvestigationOperations(
            state="available",
            tenant_id="tenant-a",
            counts={"running": 2, "awaiting-approval": 1},
            observed_at=datetime.now(timezone.utc),
            reason="Trusted tenant aggregate",
        )

    manager = _service(investigation_observer=observer)
    assert manager.investigation_operations("tenant-a").counts == {
        "running": 2,
        "awaiting-approval": 1,
    }
    assert manager.investigation_operations("tenant-b").state == "degraded"
    assert manager.investigation_operations("tenant-b").counts is None
    assert manager.investigation_operations(None).state == "not-connected"


def test_health_is_process_only_and_remote_mode_is_reported():
    manager = _service(remote_access=True)
    assert manager.health().status == "healthy"
    assert manager.health().scope == "process-only"
    assert manager.health().local_only is False
    assert manager.runtime_descriptor().management_access == "authenticated-remote"
