from __future__ import annotations

from pathlib import Path

import pytest

from cepio import (
    ExternalActionBinding,
    ExternalActionStatus,
    ExternalIdentityMapping,
    IdentityReconciliationStatus,
    UnsafeExternalRedispatchError,
    build_external_action_runtime,
)
from cepio.adapters import AdapterVerificationStatus, FakeGovernedWriteAdapter
from cepio.bootstrap import build_runtime
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject


def compressor() -> OntologyObject:
    return OntologyObject(
        id="K-201",
        type="Compressor",
        name="Recycle Gas Compressor K-201",
        properties={"criticality": "high", "riskStatus": "elevated"},
        interfaces={"RiskBearing", "MaintainableAsset", "Inspectable"},
    )


def execute_risk_action(runtime, *, correlation_id: str | None = None):
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
    result = runtime.execute_action(
        ActionRequest(
            action_type="EscalateRisk",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="reliability-1",
            actor_roles={"reliability_engineer"},
            parameters={"risk_status": "critical"},
            decision_id=decision.id,
            correlation_id=correlation_id,
            idempotency_key=f"risk:{correlation_id or 'direct'}",
        )
    )
    assert result.status.value == "executed"
    return decision, result


def configured_external_runtime(runtime, *, sqlite_path: Path | None = None):
    external = build_external_action_runtime(runtime, sqlite_path=sqlite_path)
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
    return external, adapter


def register_verified_identity(external, external_id: str = "EQ-000201"):
    return external.register_identity(
        ExternalIdentityMapping(
            cepio_object_id="K-201",
            system="fake_eam",
            identity_type="equipment",
            external_id=external_id,
            status=IdentityReconciliationStatus.verified,
        )
    )


def test_external_action_lifecycle_links_actor_decision_and_workflow_correlation():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    decision, action = execute_risk_action(runtime, correlation_id="workflow-123")
    external, adapter = configured_external_runtime(runtime)
    identity = register_verified_identity(external)

    execution = external.enqueue_from_action(action.action_id)
    assert execution.status == ExternalActionStatus.pending_execution
    assert execution.actor_id == "reliability-1"
    assert execution.decision_id == decision.id
    assert execution.workflow_instance_id == "workflow-123"
    assert execution.external_identity_id == identity.id
    assert execution.external_id == "EQ-000201"

    dispatched = external.dispatch(execution.id)
    assert dispatched.status == ExternalActionStatus.pending_verification
    assert dispatched.source_request_id is not None
    assert len(adapter.write_calls) == 1
    assert adapter.write_calls[0].actor_id == "reliability-1"
    assert adapter.write_calls[0].decision_id == decision.id

    verified = external.verify(execution.id)
    assert verified.status == ExternalActionStatus.verified
    assert verified.verified_at is not None
    assert len(adapter.verify_calls) == 1

    events = [entry.event for entry in external.history(execution.id)]
    assert events == [
        "external_write_queued",
        "adapter_dispatch_started",
        "adapter_write_acknowledged",
        "external_verification_pending",
        "verification_verified",
    ]


def test_missing_or_ambiguous_external_identity_fails_closed_before_adapter_write():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    _, action = execute_risk_action(runtime)
    external, adapter = configured_external_runtime(runtime)

    missing = external.enqueue_from_action(action.action_id)
    assert missing.status == ExternalActionStatus.failed
    assert missing.failure_reason == "identity_missing"
    assert adapter.write_calls == []

    runtime2 = build_runtime()
    runtime2.upsert_object(compressor())
    _, action2 = execute_risk_action(runtime2)
    external2, adapter2 = configured_external_runtime(runtime2)
    register_verified_identity(external2, "EQ-1")
    register_verified_identity(external2, "EQ-2")

    ambiguous = external2.enqueue_from_action(action2.action_id)
    assert ambiguous.status == ExternalActionStatus.failed
    assert ambiguous.failure_reason == "identity_ambiguous"
    assert adapter2.write_calls == []


def test_enqueue_and_dispatch_are_replay_safe():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    _, action = execute_risk_action(runtime)
    external, adapter = configured_external_runtime(runtime)
    register_verified_identity(external)

    first = external.enqueue_from_action(action.action_id)
    second = external.enqueue_from_action(action.action_id)
    assert second.id == first.id
    assert second.idempotency_key == first.idempotency_key

    dispatched = external.dispatch(first.id)
    replay = external.dispatch(first.id)
    assert dispatched.status == ExternalActionStatus.pending_verification
    assert replay.status == ExternalActionStatus.pending_verification
    assert len(adapter.write_calls) == 1


def test_unknown_write_outcome_cannot_be_blindly_redispatched_and_can_reconcile():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    _, action = execute_risk_action(runtime)
    external, adapter = configured_external_runtime(runtime)
    register_verified_identity(external)
    execution = external.enqueue_from_action(action.action_id)

    adapter.raise_on_write = TimeoutError("transport timed out after submit")
    unknown = external.dispatch(execution.id)
    assert unknown.status == ExternalActionStatus.unknown
    assert unknown.failure_reason == "adapter_write_outcome_unknown"

    with pytest.raises(UnsafeExternalRedispatchError):
        external.dispatch(execution.id)
    with pytest.raises(UnsafeExternalRedispatchError):
        external.verify(execution.id)
    assert len(adapter.write_calls) == 1

    adapter.raise_on_write = None
    adapter.reconciliation_status = AdapterVerificationStatus.verified
    reconciled = external.reconcile(execution.id)
    assert reconciled.status == ExternalActionStatus.verified
    assert len(adapter.reconcile_calls) == 1
    assert len(adapter.write_calls) == 1


def test_source_confirms_not_applied_is_terminal_failed_not_unknown():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    _, action = execute_risk_action(runtime)
    external, adapter = configured_external_runtime(runtime)
    register_verified_identity(external)
    execution = external.enqueue_from_action(action.action_id)
    external.dispatch(execution.id)

    adapter.verification_status = AdapterVerificationStatus.not_applied
    verified = external.verify(execution.id)
    assert verified.status == ExternalActionStatus.failed
    assert verified.failure_reason == "source_confirms_not_applied"


def test_external_state_and_identity_survive_sqlite_restart(tmp_path: Path):
    db = tmp_path / "cepio.db"
    runtime = build_runtime(sqlite_path=db)
    runtime.upsert_object(compressor())
    _, action = execute_risk_action(runtime, correlation_id="workflow-restart")
    external, adapter = configured_external_runtime(runtime, sqlite_path=db)
    identity = register_verified_identity(external)
    execution = external.enqueue_from_action(action.action_id)
    pending = external.dispatch(execution.id)
    assert pending.status == ExternalActionStatus.pending_verification

    external.repository.close()  # type: ignore[attr-defined]

    reloaded, reloaded_adapter = configured_external_runtime(runtime, sqlite_path=db)
    restored = reloaded.get_execution(execution.id)
    assert restored.status == ExternalActionStatus.pending_verification
    identities = reloaded.identities_for(
        "K-201", system="fake_eam", identity_type="equipment"
    )
    assert len(identities) == 1
    assert identities[0].id == identity.id

    reloaded_adapter.verification_status = AdapterVerificationStatus.verified
    verified = reloaded.verify(execution.id)
    assert verified.status == ExternalActionStatus.verified
    reloaded.repository.close()  # type: ignore[attr-defined]
    runtime.object_repository.close()  # type: ignore[attr-defined]


def test_external_write_requires_successfully_executed_cepio_action():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, _ = configured_external_runtime(runtime)
    register_verified_identity(external)

    with pytest.raises(PermissionError, match="successfully executed CEPIO Action"):
        external.enqueue_from_action("fabricated-action-id")
