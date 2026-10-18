from __future__ import annotations

import pytest

from cepio.adapters import (
    AdapterVerificationStatus,
    FakeGovernedWriteAdapter,
    GovernedVerificationRequest,
    GovernedWriteRequest,
)
from cepio.domain_bindings import ExternalRecordReference
from cepio.platform_bindings import (
    BindingCapability,
    BindingConformanceError,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
    UnsupportedBindingCapability,
    qualify_evidence_binding,
    qualify_governed_action_binding,
)


class FakeEvidenceBinding:
    manifest = PlatformBindingManifest(
        binding_id="fabric-evidence-test",
        provider_id="microsoft.fabric",
        source_system="fabric",
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
                source_system="fabric",
                source_service="onelake",
                record_kind="normalized-observation",
                record_id=external_id,
                record_version="v7",
            ),
            evidence={"normalized_value": 42.0, "unit": "bar"},
        )


def test_evidence_binding_preserves_identity_and_version_provenance():
    result = qualify_evidence_binding(FakeEvidenceBinding(), external_id="obs-42")

    assert result.binding_id == "fabric-evidence-test"
    assert result.reference_key == "fabric:normalized-observation:obs-42:v7"
    assert result.versioned is True


def test_evidence_binding_fails_closed_when_declared_version_is_missing():
    class MissingVersionBinding(FakeEvidenceBinding):
        def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
            return EvidenceEnvelope(
                reference=ExternalRecordReference(
                    source_system="fabric",
                    record_kind="normalized-observation",
                    record_id=external_id,
                )
            )

    with pytest.raises(BindingConformanceError, match="returned no record_version"):
        qualify_evidence_binding(MissingVersionBinding(), external_id="obs-42")


def test_evidence_binding_cannot_declare_governed_write_capability():
    with pytest.raises(ValueError, match="forbidden capabilities"):
        PlatformBindingManifest(
            binding_id="invalid-evidence",
            provider_id="provider",
            source_system="source",
            mode=BindingMode.evidence,
            capabilities=frozenset(
                {
                    BindingCapability.resolve_evidence,
                    BindingCapability.governed_write,
                }
            ),
        )


def test_undeclared_capability_fails_explicitly():
    with pytest.raises(UnsupportedBindingCapability, match="governed-write"):
        FakeEvidenceBinding.manifest.require(BindingCapability.governed_write)


def test_fake_adapter_qualifies_against_governed_action_contract():
    manifest = PlatformBindingManifest(
        binding_id="sap-governed-action-test",
        provider_id="sap.s4hana",
        source_system="fake_eam",
        mode=BindingMode.governed_action,
        capabilities=frozenset(
            {
                BindingCapability.governed_write,
                BindingCapability.verify,
                BindingCapability.reconcile,
            }
        ),
    )
    adapter = FakeGovernedWriteAdapter("fake_eam")
    write_request = GovernedWriteRequest(
        execution_id="exec-1",
        system="fake_eam",
        operation="create_work_order",
        external_id="WO-42",
        canonical_object_id="K-201",
        action_id="action-1",
        actor_id="reliability-engineer",
        decision_id="decision-1",
        idempotency_key="action-1:create-work-order",
        payload={"priority": "high"},
    )
    verification_request = GovernedVerificationRequest(
        execution_id="exec-1",
        system="fake_eam",
        operation="create_work_order",
        external_id="WO-42",
        canonical_object_id="K-201",
        action_id="action-1",
        idempotency_key="action-1:create-work-order",
        expected_payload={"priority": "high"},
    )

    result = qualify_governed_action_binding(
        adapter,
        manifest,
        write_request=write_request,
        verification_request=verification_request,
    )

    assert result.receipt.accepted is True
    assert result.verification.status == AdapterVerificationStatus.verified
    assert result.reconciliation.status == AdapterVerificationStatus.verified
    assert len(adapter.write_calls) == 1
    assert len(adapter.verify_calls) == 1
    assert len(adapter.reconcile_calls) == 1
