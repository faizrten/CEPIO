from __future__ import annotations

from pathlib import Path
from time import sleep

import pytest

from cepio.bootstrap import build_runtime
from cepio.kinetic import (
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepType,
)
from cepio.kinetic_resilience import (
    CompensationStatus,
    SQLiteResilienceRepository,
    StepExecutionPolicy,
    StepResilienceState,
    WorkflowControlPolicy,
    build_resilient_kinetic_runtime,
)
from cepio.model import ObjectRef, OntologyObject


def compressor(*, inspectable: bool = False) -> OntologyObject:
    interfaces = {"MaintainableAsset", "RiskBearing"}
    if inspectable:
        interfaces.add("Inspectable")
    return OntologyObject(
        id="K-201",
        type="Compressor",
        name="Recycle Gas Compressor K-201",
        properties={"criticality": "high"},
        interfaces=interfaces,
    )


def test_function_step_retries_transient_failure_then_completes():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    attempts = {"count": 0}

    def flaky_risk(*, runtime, asset_id: str) -> float:
        attempts["count"] += 1
        runtime.get_object(asset_id)
        if attempts["count"] == 1:
            raise RuntimeError("temporary calculation backend failure")
        return 0.81

    runtime.register_function("calculateAssetRisk", flaky_risk, output_type=float)
    kinetic = build_resilient_kinetic_runtime(runtime)
    kinetic.register_resilient_workflow(
        WorkflowDefinition(
            id="retry-risk",
            name="Retry risk calculation",
            steps=[
                WorkflowStepDefinition(
                    id="risk",
                    type=WorkflowStepType.function,
                    operation="calculateAssetRisk",
                    parameters={"asset_id": "${subject.id}"},
                )
            ],
        ),
        step_policies={"risk": StepExecutionPolicy(max_attempts=2)},
    )

    instance = kinetic.start_workflow(
        "retry-risk",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="reliability-1",
        actor_roles={"reliability_engineer"},
    )

    assert instance.status == WorkflowStatus.completed
    resilience = kinetic.step_resilience(instance.id, "risk")
    assert resilience.attempts == 2
    assert instance.step_states["risk"].result == 0.81
    assert "step_retry_scheduled" in [entry.event for entry in kinetic.history(instance.id)]


def test_function_timeout_retries_then_fails_terminally():
    runtime = build_runtime()
    runtime.upsert_object(compressor())

    def slow_risk(*, runtime, asset_id: str) -> float:
        runtime.get_object(asset_id)
        sleep(0.01)
        return 0.75

    runtime.register_function("calculateAssetRisk", slow_risk, output_type=float)
    kinetic = build_resilient_kinetic_runtime(runtime)
    kinetic.register_resilient_workflow(
        WorkflowDefinition(
            id="timeout-risk",
            name="Timeout risk calculation",
            steps=[
                WorkflowStepDefinition(
                    id="risk",
                    type=WorkflowStepType.function,
                    operation="calculateAssetRisk",
                    parameters={"asset_id": "${subject.id}"},
                )
            ],
        ),
        step_policies={
            "risk": StepExecutionPolicy(max_attempts=2, timeout_seconds=0.001)
        },
    )

    instance = kinetic.start_workflow(
        "timeout-risk",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="reliability-1",
        actor_roles={"reliability_engineer"},
    )

    assert instance.status == WorkflowStatus.failed
    resilience = kinetic.step_resilience(instance.id, "risk")
    assert resilience.attempts == 2
    assert resilience.timed_out is True
    assert "exceeded timeout" in (instance.step_states["risk"].error or "")


def test_cancel_compensates_completed_action():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    kinetic = build_resilient_kinetic_runtime(runtime)
    kinetic.register_resilient_workflow(
        WorkflowDefinition(
            id="cancel-risk",
            name="Cancel risk escalation",
            steps=[
                WorkflowStepDefinition(
                    id="escalate",
                    type=WorkflowStepType.action,
                    operation="EscalateRisk",
                    parameters={"risk_status": "critical"},
                ),
                WorkflowStepDefinition(
                    id="approval",
                    type=WorkflowStepType.approval,
                    approval_roles={"reliability_engineer"},
                    approval_message="Continue after risk escalation?",
                ),
            ],
        ),
        control_policy=WorkflowControlPolicy(cancel_roles={"reliability_engineer"}),
    )

    instance = kinetic.start_workflow(
        "cancel-risk",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="reliability-1",
        actor_roles={"reliability_engineer"},
    )
    assert instance.status == WorkflowStatus.waiting_for_approval
    assert runtime.get_object("K-201").properties["riskStatus"] == "critical"

    cancelled = kinetic.cancel(
        instance.id,
        actor_id="reliability-1",
        actor_roles={"reliability_engineer"},
        reason="Risk evidence invalidated",
    )

    assert cancelled.status == WorkflowStatus.cancelled
    assert runtime.get_object("K-201").properties.get("riskStatus") is None
    assert kinetic.resilience_state(instance.id).compensation_status == CompensationStatus.completed
    assert kinetic.step_resilience(instance.id, "escalate").compensated is True
    events = [entry.event for entry in kinetic.history(instance.id)]
    assert "workflow_cancellation_requested" in events
    assert "step_compensated" in events
    assert "workflow_cancelled" in events


def test_terminal_failure_compensates_prior_action():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    kinetic = build_resilient_kinetic_runtime(runtime)
    kinetic.register_resilient_workflow(
        WorkflowDefinition(
            id="failure-compensation",
            name="Failure compensation",
            steps=[
                WorkflowStepDefinition(
                    id="escalate",
                    type=WorkflowStepType.action,
                    operation="EscalateRisk",
                    parameters={"risk_status": "critical"},
                ),
                WorkflowStepDefinition(
                    id="risk",
                    type=WorkflowStepType.function,
                    operation="calculateAssetRisk",
                    parameters={"asset_id": "${input.missing_asset_id}"},
                ),
            ],
        )
    )

    instance = kinetic.start_workflow(
        "failure-compensation",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="reliability-1",
        actor_roles={"reliability_engineer"},
    )

    assert instance.status == WorkflowStatus.failed
    assert runtime.get_object("K-201").properties.get("riskStatus") is None
    resilience = kinetic.resilience_state(instance.id)
    assert resilience.compensation_status == CompensationStatus.completed
    assert kinetic.step_resilience(instance.id, "escalate").compensated is True


def test_automatic_retry_is_rejected_for_action_steps():
    runtime = build_runtime()
    kinetic = build_resilient_kinetic_runtime(runtime)
    definition = WorkflowDefinition(
        id="unsafe-action-retry",
        name="Unsafe action retry",
        steps=[
            WorkflowStepDefinition(
                id="action",
                type=WorkflowStepType.action,
                operation="EscalateRisk",
            )
        ],
    )

    with pytest.raises(ValueError, match="only supported for Function steps"):
        kinetic.register_resilient_workflow(
            definition,
            step_policies={"action": StepExecutionPolicy(max_attempts=2)},
        )


def test_resilience_state_survives_sqlite_restart(tmp_path: Path):
    db = tmp_path / "kinetic.db"
    repo = SQLiteResilienceRepository(db)
    repo.save_step_policy("wf", "step", StepExecutionPolicy(max_attempts=3, timeout_seconds=2.0))
    repo.save_step_state(
        StepResilienceState(
            instance_id="instance-1",
            step_id="step",
            attempts=2,
            last_error="temporary",
        )
    )
    repo.close()

    reopened = SQLiteResilienceRepository(db)
    policy = reopened.get_step_policy("wf", "step")
    state = reopened.get_step_state("instance-1", "step")
    assert policy is not None and policy.max_attempts == 3
    assert policy.timeout_seconds == 2.0
    assert state is not None and state.attempts == 2
    assert state.last_error == "temporary"
    reopened.close()
