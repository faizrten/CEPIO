from __future__ import annotations

import pytest

from cepio.adapters import FakeGovernedWriteAdapter
from cepio.bootstrap import build_runtime
from cepio.domain_bindings import ExternalRecordReference
from cepio.external_actions import (
    ExternalActionBinding,
    ExternalIdentityMapping,
    IdentityReconciliationStatus,
    build_external_action_runtime,
)
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject
from cepio.platform_bindings import (
    BindingCapability,
    BindingConformanceError,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
    UnsupportedBindingCapability,
    qualify_evidence_binding,
    qualify_governed_action_adapter,
    qualify_governed_action_execution,
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


def governed_manifest() -> PlatformBindingManifest:
    return PlatformBindingManifest(
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


def configured_governed_execution():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="Recycle Gas Compressor K-201",
            properties={"criticality": "high", "riskStatus": "elevated"},
            interfaces={"RiskBearing", "MaintainableAsset", "Inspectable"},
        )
    )
    decision = runtime.save_decision(
        Decision(
            subject=ObjectRef(id="K-201", type="Compressor"),
            problem="Compressor risk escalation",
            observations=["degraded condition"],
            recommendation="Escalate risk and synchronize the enterprise system",
            recommended_action="EscalateRisk",
            created_by="reliability-agent",
        )
    )
    action = runtime.execute_action(
        ActionRequest(
            action_type="EscalateRisk",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="reliability-1",
            actor_roles={"reliability_engineer"},
            parameters={"risk_status": "critical"},
            decision_id=decision.id,
            idempotency_key="binding-conformance-risk",
        )
    )

    external = build_external_action_runtime(runtime)
    adapter = FakeGovernedWriteAdapter("fake_eam")
    external.register_adapter(adapter)
    external.register_binding(
        ExternalActionBinding(
            action_type="EscalateRisk",
            system="fake_eam",
            operation="update_risk_status",
            identity_type="equipment",
        )
    )
    external.register_identity(
        ExternalIdentityMapping(
            cepio_object_id="K-201",
            system="fake_eam",
            identity_type="equipment",
            external_id="EQ-000201",
            status=IdentityReconciliationStatus.verified,
        )
    )
    execution = external.enqueue_from_action(action.action_id)
    return external, adapter, execution


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


def test_fake_adapter_matches_governed_action_binding_shape():
    adapter = FakeGovernedWriteAdapter("fake_eam")
    qualify_governed_action_adapter(adapter, governed_manifest())
    assert adapter.write_calls == []


@pytest.mark.parametrize("verification_path", ["verify", "reconcile"])
def test_governed_action_conformance_dispatches_only_through_action_runtime(verification_path):
    external, adapter, execution = configured_governed_execution()

    result = qualify_governed_action_execution(
        external,
        governed_manifest(),
        execution_id=execution.id,
        verification_path=verification_path,
    )

    assert result.status.value == "verified"
    assert result.dispatch_attempts == 1
    assert result.verification_attempts == 1
    assert len(adapter.write_calls) == 1
    if verification_path == "verify":
        assert len(adapter.verify_calls) == 1
        assert adapter.reconcile_calls == []
    else:
        assert len(adapter.reconcile_calls) == 1
        assert adapter.verify_calls == []
