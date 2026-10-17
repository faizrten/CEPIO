from pathlib import Path

import pytest

from cepio import (
    ExternalActionBinding,
    ExternalActionStatus,
    ExternalIdentityMapping,
    IdentityReconciliationStatus,
    WorkflowDefinition,
    WorkflowOutcomeStatus,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepStatus,
    WorkflowStepType,
    build_external_action_runtime,
    build_external_kinetic_runtime,
    build_external_resilient_kinetic_runtime,
)
from cepio.adapters import AdapterVerificationStatus, FakeGovernedWriteAdapter
from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject


def compressor() -> OntologyObject:
    return OntologyObject(
        id="K-201",
        type="Compressor",
        name="Recycle Gas Compressor K-201",
        properties={"criticality": "safety_critical"},
        interfaces={"Inspectable", "MaintainableAsset", "RiskBearing"},
    )


def verification_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="verified-inspection",
        name="Verified inspection creation",
        version="0.4.0",
        steps=[
            WorkflowStepDefinition(
                id="calculate-risk",
                type=WorkflowStepType.function,
                operation="calculateAssetRisk",
                parameters={"asset_id": "${subject.id}"},
            ),
            WorkflowStepDefinition(
                id="recommend-inspection",
                type=WorkflowStepType.decision,
                decision_problem="Should this asset be inspected?",
                decision_recommendation="Create an inspection and verify enterprise synchronization.",
                recommended_action="CreateInspection",
            ),
            WorkflowStepDefinition(
                id="human-approval",
                type=WorkflowStepType.approval,
                approval_roles={"maintenance_engineer"},
                approval_message="Approve verified inspection creation.",
            ),
            WorkflowStepDefinition(
                id="create-inspection",
                type=WorkflowStepType.action,
                operation="CreateInspection",
                parameters={"title": "Externally verified workflow inspection"},
            ),
            WorkflowStepDefinition(
                id="verify-external",
                type=WorkflowStepType.external_verification,
                action_step_id="create-inspection",
            ),
        ],
    )


def configure_external(runtime, *, sqlite_path: Path | None = None):
    external = build_external_action_runtime(runtime, sqlite_path=sqlite_path)
    adapter = FakeGovernedWriteAdapter("fake_eam")
    external.register_adapter(adapter)
    external.register_binding(
        ExternalActionBinding(
            action_type="CreateInspection",
            system="fake_eam",
            operation="create_inspection",
            identity_type="equipment",
        )
    )
    return external, adapter


def register_identity(external):
    return external.register_identity(
        ExternalIdentityMapping(
            cepio_object_id="K-201",
            system="fake_eam",
            identity_type="equipment",
            external_id="EQ-000201",
            status=IdentityReconciliationStatus.verified,
        )
    )


def start_to_external_wait(kinetic):
    kinetic.register_workflow(verification_workflow())
    paused = kinetic.start_workflow(
        "verified-inspection",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
        trigger_key="condition:K-201:verified-inspection",
    )
    assert paused.status == WorkflowStatus.waiting_for_approval
    approval = kinetic.pending_approval(paused.id)
    assert approval is not None
    waiting = kinetic.decide_approval(
        approval.id,
        actor_id="maint-1",
        actor_roles={"maintenance_engineer"},
        approved=True,
    )
    return waiting


def test_workflow_waits_for_verified_external_completion_then_records_one_outcome():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, adapter = configure_external(runtime)
    register_identity(external)
    kinetic = build_external_kinetic_runtime(runtime, external)

    waiting = start_to_external_wait(kinetic)
    assert waiting.status == WorkflowStatus.waiting_for_external_verification
    gate = waiting.step_states["verify-external"]
    assert gate.status == WorkflowStepStatus.waiting_for_external_verification
    assert gate.external_execution_id is not None
    assert adapter.write_calls == []

    execution = external.get_execution(gate.external_execution_id)
    assert execution.status == ExternalActionStatus.pending_execution
    assert execution.workflow_instance_id == waiting.id
    assert execution.action_id == waiting.step_states["create-inspection"].action_id

    assert kinetic.resume(waiting.id).status == WorkflowStatus.waiting_for_external_verification
    assert adapter.write_calls == []

    after_dispatch = kinetic.tick_external_verification(waiting.id)
    assert after_dispatch.status == WorkflowStatus.waiting_for_external_verification
    assert external.get_execution(execution.id).status == ExternalActionStatus.pending_verification
    assert len(adapter.write_calls) == 1
    assert adapter.verify_calls == []
    assert kinetic.outcomes(waiting.id) == []

    completed = kinetic.tick_external_verification(waiting.id)
    assert completed.status == WorkflowStatus.completed
    assert len(adapter.write_calls) == 1
    assert len(adapter.verify_calls) == 1

    outcomes = kinetic.outcomes(waiting.id)
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == WorkflowOutcomeStatus.verified
    assert outcome.action_id == completed.step_states["create-inspection"].action_id
    assert outcome.external_execution_id == execution.id
    assert completed.step_states["verify-external"].outcome_id == outcome.id

    replay = kinetic.tick_external_verification(waiting.id)
    assert replay.status == WorkflowStatus.completed
    assert len(adapter.write_calls) == 1
    assert len(adapter.verify_calls) == 1
    assert len(kinetic.outcomes(waiting.id)) == 1


def test_missing_identity_fails_gate_closed_and_records_failed_outcome():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, adapter = configure_external(runtime)
    kinetic = build_external_kinetic_runtime(runtime, external)

    failed = start_to_external_wait(kinetic)
    assert failed.status == WorkflowStatus.failed
    assert adapter.write_calls == []
    gate = failed.step_states["verify-external"]
    assert gate.status == WorkflowStepStatus.failed
    assert gate.external_execution_id is not None

    execution = external.get_execution(gate.external_execution_id)
    assert execution.status == ExternalActionStatus.failed
    assert execution.failure_reason == "identity_missing"
    outcomes = kinetic.outcomes(failed.id)
    assert len(outcomes) == 1
    assert outcomes[0].status == WorkflowOutcomeStatus.failed


def test_unknown_write_outcome_stays_waiting_until_explicit_reconciliation():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, adapter = configure_external(runtime)
    register_identity(external)
    kinetic = build_external_kinetic_runtime(runtime, external)

    waiting = start_to_external_wait(kinetic)
    gate = waiting.step_states["verify-external"]
    execution_id = gate.external_execution_id
    assert execution_id is not None

    adapter.raise_on_write = TimeoutError("transport timed out after submit")
    unknown_wait = kinetic.tick_external_verification(waiting.id)
    assert unknown_wait.status == WorkflowStatus.waiting_for_external_verification
    assert external.get_execution(execution_id).status == ExternalActionStatus.unknown
    assert len(adapter.write_calls) == 1
    assert kinetic.outcomes(waiting.id) == []

    assert kinetic.resume(waiting.id).status == WorkflowStatus.waiting_for_external_verification
    unchanged = kinetic.tick_external_verification(waiting.id)
    assert unchanged.status == WorkflowStatus.waiting_for_external_verification
    assert len(adapter.write_calls) == 1
    assert adapter.reconcile_calls == []

    adapter.raise_on_write = None
    adapter.reconciliation_status = AdapterVerificationStatus.verified
    completed = kinetic.tick_external_verification(
        waiting.id, reconcile_unknown=True
    )
    assert completed.status == WorkflowStatus.completed
    assert len(adapter.write_calls) == 1
    assert len(adapter.reconcile_calls) == 1
    assert len(kinetic.outcomes(waiting.id)) == 1
    assert kinetic.outcomes(waiting.id)[0].status == WorkflowOutcomeStatus.verified


def test_source_not_applied_fails_workflow_with_terminal_outcome():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, adapter = configure_external(runtime)
    register_identity(external)
    kinetic = build_external_kinetic_runtime(runtime, external)

    waiting = start_to_external_wait(kinetic)
    kinetic.tick_external_verification(waiting.id)
    adapter.verification_status = AdapterVerificationStatus.not_applied
    failed = kinetic.tick_external_verification(waiting.id)

    assert failed.status == WorkflowStatus.failed
    assert len(adapter.write_calls) == 1
    assert len(adapter.verify_calls) == 1
    outcomes = kinetic.outcomes(waiting.id)
    assert len(outcomes) == 1
    assert outcomes[0].status == WorkflowOutcomeStatus.failed
    assert outcomes[0].evidence["failure_reason"] == "source_confirms_not_applied"


def test_sqlite_restart_preserves_external_gate_execution_and_outcome(tmp_path: Path):
    database = tmp_path / "cepio.db"

    runtime1 = build_runtime(sqlite_path=database)
    runtime1.upsert_object(compressor())
    external1, adapter1 = configure_external(runtime1, sqlite_path=database)
    register_identity(external1)
    kinetic1 = build_external_kinetic_runtime(
        runtime1, external1, sqlite_path=database
    )

    waiting = start_to_external_wait(kinetic1)
    after_dispatch = kinetic1.tick_external_verification(waiting.id)
    assert after_dispatch.status == WorkflowStatus.waiting_for_external_verification
    execution_id = after_dispatch.step_states["verify-external"].external_execution_id
    assert execution_id is not None
    assert len(adapter1.write_calls) == 1

    external1.repository.close()  # type: ignore[attr-defined]
    kinetic1.repository.close()  # type: ignore[attr-defined]
    kinetic1.outcome_repository.close()  # type: ignore[attr-defined]

    runtime2 = build_runtime(sqlite_path=database)
    external2, adapter2 = configure_external(runtime2, sqlite_path=database)
    kinetic2 = build_external_kinetic_runtime(
        runtime2, external2, sqlite_path=database
    )

    restored = kinetic2.get_instance(waiting.id)
    assert restored.status == WorkflowStatus.waiting_for_external_verification
    assert restored.step_states["verify-external"].external_execution_id == execution_id
    assert external2.get_execution(execution_id).status == ExternalActionStatus.pending_verification

    completed = kinetic2.tick_external_verification(waiting.id)
    assert completed.status == WorkflowStatus.completed
    assert adapter2.write_calls == []
    assert len(adapter2.verify_calls) == 1
    outcome = kinetic2.outcome_for_step(waiting.id, "verify-external")
    assert outcome is not None
    assert outcome.status == WorkflowOutcomeStatus.verified

    kinetic2.outcome_repository.close()  # type: ignore[attr-defined]
    kinetic2.repository.close()  # type: ignore[attr-defined]
    external2.repository.close()  # type: ignore[attr-defined]


def test_external_verification_definition_is_source_neutral_and_references_prior_action():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, _ = configure_external(runtime)
    kinetic = build_external_kinetic_runtime(runtime, external)

    with pytest.raises(ValueError, match="earlier Action"):
        kinetic.register_workflow(
            WorkflowDefinition(
                id="bad-order",
                name="Bad order",
                steps=[
                    WorkflowStepDefinition(
                        id="verify-first",
                        type=WorkflowStepType.external_verification,
                        action_step_id="create-later",
                    ),
                    WorkflowStepDefinition(
                        id="create-later",
                        type=WorkflowStepType.action,
                        operation="CreateInspection",
                    ),
                ],
            )
        )

    with pytest.raises(ValueError, match="must not name a source operation"):
        kinetic.register_workflow(
            WorkflowDefinition(
                id="source-leak",
                name="Source leaking gate",
                steps=[
                    WorkflowStepDefinition(
                        id="create",
                        type=WorkflowStepType.action,
                        operation="CreateInspection",
                    ),
                    WorkflowStepDefinition(
                        id="verify",
                        type=WorkflowStepType.external_verification,
                        action_step_id="create",
                        operation="sap.update",
                    ),
                ],
            )
        )


def test_external_resilient_runtime_supports_same_verification_gate():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    external, adapter = configure_external(runtime)
    register_identity(external)
    kinetic = build_external_resilient_kinetic_runtime(runtime, external)

    kinetic.register_resilient_workflow(verification_workflow())
    paused = kinetic.start_workflow(
        "verified-inspection",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
        trigger_key="condition:K-201:resilient",
    )
    approval = kinetic.pending_approval(paused.id)
    assert approval is not None
    waiting = kinetic.decide_approval(
        approval.id,
        actor_id="maint-1",
        actor_roles={"maintenance_engineer"},
        approved=True,
    )
    assert waiting.status == WorkflowStatus.waiting_for_external_verification

    kinetic.tick_external_verification(waiting.id)
    completed = kinetic.tick_external_verification(waiting.id)
    assert completed.status == WorkflowStatus.completed
    assert len(adapter.write_calls) == 1
    assert len(adapter.verify_calls) == 1
    assert len(kinetic.outcomes(waiting.id)) == 1
