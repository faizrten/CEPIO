import pytest

from cepio.bootstrap import build_kinetic_runtime, build_runtime
from cepio.kinetic import (
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepType,
)
from cepio.model import ObjectRef, OntologyObject


def reliability_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="asset-risk-inspection",
        name="Asset risk inspection",
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
                decision_problem="Should the asset be inspected?",
                decision_recommendation="Inspect the asset before further degradation.",
                recommended_action="CreateInspection",
            ),
            WorkflowStepDefinition(
                id="human-approval",
                type=WorkflowStepType.approval,
                approval_roles={"maintenance_engineer"},
                approval_message="Approve creation of the inspection.",
            ),
            WorkflowStepDefinition(
                id="create-inspection",
                type=WorkflowStepType.action,
                operation="CreateInspection",
                parameters={"title": "Workflow inspection"},
            ),
        ],
    )


def add_compressor(runtime) -> None:
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={"criticality": "safety_critical"},
            interfaces={"Inspectable", "MaintainableAsset"},
        )
    )


def test_agent_workflow_pauses_for_human_then_executes_governed_action():
    runtime = build_runtime()
    add_compressor(runtime)
    kinetic = build_kinetic_runtime(runtime)
    kinetic.register_workflow(reliability_workflow())

    paused = kinetic.start_workflow(
        "asset-risk-inspection",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
        trigger_key="trip:K-201:001",
    )

    assert paused.status == WorkflowStatus.waiting_for_approval
    assert paused.step_states["calculate-risk"].result == 0.6
    decision_id = paused.step_states["recommend-inspection"].decision_id
    assert decision_id is not None
    assert runtime.get_decision(decision_id).recommended_action == "CreateInspection"

    approval = kinetic.pending_approval(paused.id)
    assert approval is not None
    with pytest.raises(PermissionError):
        kinetic.decide_approval(
            approval.id,
            actor_id="operator-1",
            actor_roles={"operator"},
            approved=True,
        )

    completed = kinetic.decide_approval(
        approval.id,
        actor_id="maint-1",
        actor_roles={"maintenance_engineer"},
        approved=True,
        comment="Proceed with inspection.",
    )

    assert completed.status == WorkflowStatus.completed
    assert completed.last_actor_id == "maint-1"
    assert len(runtime.neighbors("K-201", "hasInspection")) == 1
    action_result = completed.step_states["create-inspection"].result
    assert action_result["effects"]["inspection_id"]
    assert action_result["replayed"] is False

    replay = kinetic.start_workflow(
        "asset-risk-inspection",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
        trigger_key="trip:K-201:001",
    )
    assert replay.id == completed.id
    assert len(runtime.neighbors("K-201", "hasInspection")) == 1

    events = [entry.event for entry in kinetic.history(completed.id)]
    assert events[0] == "workflow_started"
    assert "approval_requested" in events
    assert "approval_granted" in events
    assert events[-1] == "workflow_completed"


def test_sqlite_workflow_survives_repository_restart(tmp_path):
    database = tmp_path / "cepio.db"

    runtime1 = build_runtime(sqlite_path=database)
    add_compressor(runtime1)
    kinetic1 = build_kinetic_runtime(runtime1, sqlite_path=database)
    kinetic1.register_workflow(reliability_workflow())
    paused = kinetic1.start_workflow(
        "asset-risk-inspection",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
        trigger_key="trip:K-201:restart",
    )
    approval = kinetic1.pending_approval(paused.id)
    assert approval is not None

    runtime2 = build_runtime(sqlite_path=database)
    kinetic2 = build_kinetic_runtime(runtime2, sqlite_path=database)

    restored = kinetic2.get_instance(paused.id)
    assert restored.status == WorkflowStatus.waiting_for_approval
    restored_approval = kinetic2.pending_approval(paused.id)
    assert restored_approval is not None
    assert restored_approval.id == approval.id

    completed = kinetic2.decide_approval(
        restored_approval.id,
        actor_id="maint-2",
        actor_roles={"maintenance_engineer"},
        approved=True,
    )
    assert completed.status == WorkflowStatus.completed
    assert len(runtime2.neighbors("K-201", "hasInspection")) == 1
    assert [entry.event for entry in kinetic2.history(paused.id)][-1] == "workflow_completed"
