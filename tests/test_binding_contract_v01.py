from __future__ import annotations

import pytest

from cepio.adapters import FakeGovernedWriteAdapter
from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.config import RuntimeSettings
from cepio.domain_bindings import ExternalRecordReference
from cepio.management_contract import BindingDescriptor
from cepio.management_runtime import (
    build_management_service,
    build_management_service_from_registrations,
)
from cepio.platform_bindings import (
    BINDING_CONTRACT_VERSION,
    BindingCapability,
    BindingConformanceError,
    BindingMode,
    BindingRuntimeStatus,
    EvidenceEnvelope,
    PlatformBindingManifest,
    register_evidence_binding,
    register_governed_action_binding,
)


class FakeEvidenceBinding:
    manifest = PlatformBindingManifest(
        binding_id="cepio.binding.fabric.observation-test",
        provider_id="microsoft-fabric",
        source_system="microsoft-fabric",
        mode=BindingMode.evidence,
        capabilities=frozenset(
            {
                BindingCapability.resolve_evidence,
                BindingCapability.versioned_identity,
            }
        ),
    )

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        return EvidenceEnvelope(
            reference=ExternalRecordReference(
                source_system="microsoft-fabric",
                record_kind="normalized-observation",
                record_id=external_id,
                record_version="7",
            ),
            evidence={"value": 42.0},
        )


def _settings() -> RuntimeSettings:
    return RuntimeSettings(
        environment="test",
        db_url="memory://",
        resource_root=None,
        ontology_dir=None,
        profiles=(),
        validate_types=True,
        validate_properties=True,
        strict_properties=False,
    )


def _auth() -> AuthSettings:
    return AuthSettings(
        mode="dev",
        environment="test",
        tenant_id=None,
        audience=None,
        issuer=None,
        jwks_uri=None,
        group_role_map={},
    )


def _governed_manifest() -> PlatformBindingManifest:
    return PlatformBindingManifest(
        binding_id="cepio.binding.sap.work-management-test",
        provider_id="sap-s4hana",
        source_system="sap-eam",
        mode=BindingMode.governed_action,
        capabilities=frozenset(
            {
                BindingCapability.governed_write,
                BindingCapability.verify,
                BindingCapability.reconcile,
            }
        ),
    )


def test_evidence_registration_derives_access_authority_and_capabilities():
    registration = register_evidence_binding(
        FakeEvidenceBinding(),
        capability_id="industrial-observation",
    )

    assert registration.contract_version == BINDING_CONTRACT_VERSION
    assert registration.manifest.binding_id == "cepio.binding.fabric.observation-test"
    assert registration.access_mode == "read"
    assert registration.authority == "observation-only"
    assert registration.declared_capabilities == (
        "resolve-evidence",
        "versioned-identity",
    )


def test_management_descriptor_is_derived_from_binding_registration_truth():
    registration = register_evidence_binding(
        FakeEvidenceBinding(),
        capability_id="industrial-observation",
        status=BindingRuntimeStatus.degraded,
    )

    descriptor = BindingDescriptor.from_registration(registration)

    assert descriptor.binding_id == registration.manifest.binding_id
    assert descriptor.provider == registration.manifest.provider_id
    assert descriptor.source_system == registration.manifest.source_system
    assert descriptor.capability == registration.capability_id
    assert descriptor.mode == registration.access_mode
    assert descriptor.status == "degraded"
    assert descriptor.authority == registration.authority
    assert descriptor.binding_contract_version == BINDING_CONTRACT_VERSION
    assert descriptor.declared_capabilities == [
        "resolve-evidence",
        "versioned-identity",
    ]


def test_management_runtime_accepts_canonical_binding_registrations():
    registration = register_evidence_binding(
        FakeEvidenceBinding(),
        capability_id="industrial-observation",
    )
    management = build_management_service_from_registrations(
        build_runtime(),
        runtime_settings=_settings(),
        auth_settings=_auth(),
        binding_registrations=[registration],
    )

    bindings = management.list_bindings()
    capabilities = management.capabilities()

    assert len(bindings) == 1
    assert bindings[0].binding_id == registration.manifest.binding_id
    assert bindings[0].provider == "microsoft-fabric"
    assert bindings[0].mode == "read"
    assert capabilities.binding_count == 1
    assert capabilities.binding_contract_version == BINDING_CONTRACT_VERSION


def test_legacy_management_descriptor_construction_remains_supported():
    legacy = BindingDescriptor(
        binding_id="legacy",
        provider="provider",
        capability="observation",
        mode="read",
        status="ready",
        authority="observation-only",
    )
    management = build_management_service(
        build_runtime(),
        runtime_settings=_settings(),
        auth_settings=_auth(),
        bindings=[legacy],
    )

    assert management.list_bindings() == [legacy]


def test_registration_rejects_blank_capability_id():
    with pytest.raises(ValueError, match="capability_id"):
        register_evidence_binding(FakeEvidenceBinding(), capability_id="   ")


def test_evidence_registration_rejects_governed_manifest():
    class WrongBinding:
        manifest = _governed_manifest()

        def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
            raise AssertionError("must not resolve")

    with pytest.raises(BindingConformanceError, match="requires an evidence"):
        register_evidence_binding(WrongBinding(), capability_id="observation")


def test_evidence_registration_rejects_missing_resolver():
    class MissingResolver:
        manifest = FakeEvidenceBinding.manifest
        resolve_evidence = None

    with pytest.raises(BindingConformanceError, match="does not implement resolve_evidence"):
        register_evidence_binding(MissingResolver(), capability_id="observation")


def test_evidence_registration_rejects_write_surface():
    class LeakyEvidenceBinding(FakeEvidenceBinding):
        def write_governed(self) -> None:
            raise AssertionError("must not write")

    with pytest.raises(BindingConformanceError, match="must not expose"):
        register_evidence_binding(LeakyEvidenceBinding(), capability_id="observation")


def test_governed_action_registration_derives_write_authority_without_dispatch():
    adapter = FakeGovernedWriteAdapter("sap-eam")
    registration = register_governed_action_binding(
        adapter,
        _governed_manifest(),
        capability_id="work-management",
    )
    descriptor = BindingDescriptor.from_registration(registration)

    assert registration.access_mode == "write"
    assert registration.authority == "governed-action"
    assert registration.declared_capabilities == (
        "governed-write",
        "reconcile",
        "verify",
    )
    assert descriptor.mode == "write"
    assert descriptor.authority == "governed-action"
    assert adapter.write_calls == []
