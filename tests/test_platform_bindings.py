from __future__ import annotations

from types import SimpleNamespace

import pytest

from cepio.adapters import FakeGovernedWriteAdapter
from cepio.bootstrap import build_runtime
from cepio.domain_bindings import ExternalRecordReference
from cepio.external_actions import (
    ExternalActionBinding,
    ExternalActionStatus,
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


def evidence_manifest(*, versioned: bool = True) -> PlatformBindingManifest:
    capabilities = {BindingCapability.resolve_evidence}
    if versioned:
        capabilities.add(BindingCapability.versioned_identity)
    return PlatformBindingManifest(
        binding_id="evidence-test",
        provider_id="provider",
        source_system="fabric",
        mode=BindingMode.evidence,
        capabilities=frozenset(capabilities),
    )


def governed_manifest(*, source_system: str = "fake_eam") -> PlatformBindingManifest:
    return PlatformBindingManifest(
        binding_id="sap-governed-action-test",
        provider_id="sap.s4hana",
        source_system=source_system,
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


@pytest.mark.parametrize("field", ["binding_id", "provider_id", "source_system"])
def test_manifest_rejects_blank_identity_fields(field):
    kwargs = {
        "binding_id": "binding",
        "provider_id": "provider",
        "source_system": "source",
        "mode": BindingMode.evidence,
        "capabilities": frozenset({BindingCapability.resolve_evidence}),
    }
    kwargs[field] = "   "
    with pytest.raises(ValueError, match="must be non-empty"):
        PlatformBindingManifest(**kwargs)


def test_evidence_manifest_requires_resolve_capability():
    with pytest.raises(ValueError, match="missing required capabilities"):
        PlatformBindingManifest(
            binding_id="invalid",
            provider_id="provider",
            source_system="source",
            mode=BindingMode.evidence,
            capabilities=frozenset(),
        )


def test_governed_manifest_requires_all_action_capabilities():
    with pytest.raises(ValueError, match="missing required capabilities"):
        PlatformBindingManifest(
            binding_id="invalid",
            provider_id="provider",
            source_system="source",
            mode=BindingMode.governed_action,
            capabilities=frozenset({BindingCapability.governed_write}),
        )


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


def test_governed_binding_cannot_declare_evidence_capability():
    with pytest.raises(ValueError, match="forbidden capabilities"):
        PlatformBindingManifest(
            binding_id="invalid-action",
            provider_id="provider",
            source_system="source",
            mode=BindingMode.governed_action,
            capabilities=frozenset(
                {
                    BindingCapability.governed_write,
                    BindingCapability.verify,
                    BindingCapability.reconcile,
                    BindingCapability.resolve_evidence,
                }
            ),
        )


def test_undeclared_capability_fails_explicitly():
    with pytest.raises(UnsupportedBindingCapability, match="governed-write"):
        FakeEvidenceBinding.manifest.require(BindingCapability.governed_write)


def test_evidence_binding_preserves_identity_and_version_provenance():
    result = qualify_evidence_binding(FakeEvidenceBinding(), external_id="obs-42")
    assert result.binding_id == "fabric-evidence-test"
    assert result.reference_key == "fabric:normalized-observation:obs-42:v7"
    assert result.versioned is True


def test_evidence_binding_can_return_unversioned_identity_when_not_declared():
    class UnversionedBinding:
        manifest = evidence_manifest(versioned=False)

        def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
            return EvidenceEnvelope(
                reference=ExternalRecordReference(
                    source_system="fabric",
                    record_kind="observation",
                    record_id=external_id,
                )
            )

    result = qualify_evidence_binding(UnversionedBinding(), external_id="obs-42")
    assert result.versioned is False


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


def test_evidence_qualification_rejects_wrong_manifest_mode():
    class WrongModeBinding:
        manifest = governed_manifest()

        def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
            raise AssertionError("must not be called")

    with pytest.raises(BindingConformanceError, match="requires an evidence binding"):
        qualify_evidence_binding(WrongModeBinding(), external_id="obs")


def test_evidence_binding_rejects_write_surface():
    class WritableEvidenceBinding(FakeEvidenceBinding):
        def write_governed(self):
            return None

    with pytest.raises(BindingConformanceError, match="must not expose"):
        qualify_evidence_binding(WritableEvidenceBinding(), external_id="obs")


def test_evidence_binding_rejects_source_identity_drift():
    class WrongSourceBinding(FakeEvidenceBinding):
        def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
            return EvidenceEnvelope(
                reference=ExternalRecordReference(
                    source_system="wrong",
                    record_kind="observation",
                    record_id=external_id,
                    record_version="v1",
                )
            )

    with pytest.raises(BindingConformanceError, match="source_system"):
        qualify_evidence_binding(WrongSourceBinding(), external_id="obs")


def test_evidence_binding_rejects_record_identity_drift():
    class WrongRecordBinding(FakeEvidenceBinding):
        def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
            return EvidenceEnvelope(
                reference=ExternalRecordReference(
                    source_system="fabric",
                    record_kind="observation",
                    record_id="different",
                    record_version="v1",
                )
            )

    with pytest.raises(BindingConformanceError, match="identity changed"):
        qualify_evidence_binding(WrongRecordBinding(), external_id="obs")


def test_fake_adapter_matches_governed_action_binding_shape():
    adapter = FakeGovernedWriteAdapter("fake_eam")
    qualify_governed_action_adapter(adapter, governed_manifest())
    assert adapter.write_calls == []


def test_governed_adapter_qualification_rejects_evidence_manifest():
    adapter = FakeGovernedWriteAdapter("fake_eam")
    with pytest.raises(BindingConformanceError, match="requires a governed-action"):
        qualify_governed_action_adapter(adapter, evidence_manifest())


def test_governed_adapter_qualification_rejects_source_mismatch():
    adapter = FakeGovernedWriteAdapter("other")
    with pytest.raises(BindingConformanceError, match="system_name"):
        qualify_governed_action_adapter(adapter, governed_manifest())


def test_governed_adapter_qualification_rejects_missing_method():
    class BrokenAdapter:
        system_name = "fake_eam"
        write_governed = None
        verify_write = None
        reconcile_write = None

    with pytest.raises(BindingConformanceError, match="write_governed"):
        qualify_governed_action_adapter(BrokenAdapter(), governed_manifest())


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


def test_execution_qualification_rejects_evidence_manifest():
    external, _, execution = configured_governed_execution()
    with pytest.raises(BindingConformanceError, match="requires a governed-action"):
        qualify_governed_action_execution(external, evidence_manifest(), execution_id=execution.id)


def test_execution_qualification_rejects_system_mismatch():
    external, _, execution = configured_governed_execution()
    with pytest.raises(BindingConformanceError, match="system does not match"):
        qualify_governed_action_execution(
            external, governed_manifest(source_system="other"), execution_id=execution.id
        )


def test_execution_qualification_requires_pending_state():
    external, _, execution = configured_governed_execution()
    external.dispatch(execution.id)
    with pytest.raises(BindingConformanceError, match="pending_execution"):
        qualify_governed_action_execution(external, governed_manifest(), execution_id=execution.id)


class ScriptedExternalRuntime:
    def __init__(self, *, dispatch_attempts=(1, 1), terminal_status=ExternalActionStatus.verified):
        self.dispatch_attempts = list(dispatch_attempts)
        self.terminal_status = terminal_status

    def get_execution(self, execution_id):
        return SimpleNamespace(
            id=execution_id,
            system="fake_eam",
            status=ExternalActionStatus.pending_execution,
            dispatch_attempts=0,
            verification_attempts=0,
        )

    def dispatch(self, execution_id):
        attempts = self.dispatch_attempts.pop(0)
        return SimpleNamespace(id=execution_id, dispatch_attempts=attempts)

    def verify(self, execution_id):
        return SimpleNamespace(
            id=execution_id,
            status=self.terminal_status,
            dispatch_attempts=1,
            verification_attempts=1,
        )

    reconcile = verify


def test_execution_qualification_rejects_replay_that_advances_attempt_count():
    runtime = ScriptedExternalRuntime(dispatch_attempts=(1, 2))
    with pytest.raises(BindingConformanceError, match="Repeated dispatch advanced"):
        qualify_governed_action_execution(runtime, governed_manifest(), execution_id="exec-1")


def test_execution_qualification_rejects_non_single_initial_dispatch():
    runtime = ScriptedExternalRuntime(dispatch_attempts=(2, 2))
    with pytest.raises(BindingConformanceError, match="exactly once"):
        qualify_governed_action_execution(runtime, governed_manifest(), execution_id="exec-1")


def test_execution_qualification_requires_verified_terminal_outcome():
    runtime = ScriptedExternalRuntime(terminal_status=ExternalActionStatus.pending_verification)
    with pytest.raises(BindingConformanceError, match="verified external outcome"):
        qualify_governed_action_execution(runtime, governed_manifest(), execution_id="exec-1")
