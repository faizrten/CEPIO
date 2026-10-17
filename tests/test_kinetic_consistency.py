from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from cepio.bootstrap import build_kinetic_runtime, build_runtime
from cepio.kinetic import (
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepType,
)
from cepio.kinetic_resilience import (
    ResilientKineticRuntime,
    StepExecutionPolicy,
)
from cepio.model import ObjectRef, OntologyObject


def add_compressor(runtime) -> None:
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={"criticality": "high"},
            interfaces={"Inspectable", "MaintainableAsset"},
        )
    )


def versioned_workflow(version: str, action: str) -> WorkflowDefinition:
    return WorkflowDefinition(
        id="versioned-maintenance",
        name="Versioned maintenance",
        version=version,
        steps=[
            WorkflowStepDefinition(
                id="approval",
                type=WorkflowStepType.approval,
                approval_roles={"maintenance_engineer"},
                approval_message=f"Approve {version}",
            ),
            WorkflowStepDefinition(
                id="execute",
                type=WorkflowStepType.action,
                operation=action,
                parameters={"title": f"workflow-{version}"},
            ),
        ],
    )


def trigger_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="trigger-once",
        name="Trigger once",
        version="1.0.0",
        steps=[
            WorkflowStepDefinition(
                id="approval",
                type=WorkflowStepType.approval,
                approval_roles={"maintenance_engineer"},
            )
        ],
    )


def test_paused_instance_resumes_exact_pinned_definition_version():
    runtime = build_runtime()
    add_compressor(runtime)
    kinetic = build_kinetic_runtime(runtime)
    kinetic.register_workflow(versioned_workflow("1.0.0", "CreateInspection"))

    paused = kinetic.start_workflow(
        "versioned-maintenance",
        definition_version="1.0.0",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="agent-1",
        actor_roles={"ai_agent_recommender"},
        trigger_key="versioned:K-201:1",
    )
    assert paused.status == WorkflowStatus.waiting_for_approval
    assert paused.definition_version == "1.0.0"

    kinetic.register_workflow(versioned_workflow("2.0.0", "CreateWorkOrder"))
    approval = kinetic.pending_approval(paused.id)
    assert approval is not None

    completed = kinetic.decide_approval(
        approval.id,
        actor_id="maint-1",
        actor_roles={"maintenance_engineer"},
        approved=True,
    )
    assert completed.status == WorkflowStatus.completed
    assert completed.definition_version == "1.0.0"
    assert len(runtime.neighbors("K-201", "hasInspection")) == 1
    assert len(runtime.neighbors("K-201", "hasWorkOrder")) == 0


def test_same_workflow_id_and_version_is_immutable():
    runtime = build_runtime()
    add_compressor(runtime)
    kinetic = build_kinetic_runtime(runtime)
    kinetic.register_workflow(versioned_workflow("1.0.0", "CreateInspection"))

    with pytest.raises(ValueError, match="immutable"):
        kinetic.register_workflow(versioned_workflow("1.0.0", "CreateWorkOrder"))


def test_atomic_trigger_create_or_get_in_memory():
    runtime = build_runtime()
    add_compressor(runtime)
    kinetic = build_kinetic_runtime(runtime)
    kinetic.register_workflow(trigger_workflow())

    def start_once():
        return kinetic.start_workflow(
            "trigger-once",
            subject=ObjectRef(id="K-201", type="Compressor"),
            actor_id="agent-1",
            actor_roles={"ai_agent_recommender"},
            trigger_key="same-trigger",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        instances = list(pool.map(lambda _: start_once(), range(8)))

    assert len({instance.id for instance in instances}) == 1
    workflow_id = instances[0].id
    events = [entry.event for entry in kinetic.history(workflow_id)]
    assert events.count("workflow_started") == 1
    assert events.count("approval_requested") == 1


def test_atomic_trigger_create_or_get_across_sqlite_connections(tmp_path):
    database = tmp_path / "kinetic-consistency.db"
    runtime = build_runtime()
    add_compressor(runtime)
    kinetic1 = build_kinetic_runtime(runtime, sqlite_path=database)
    kinetic2 = build_kinetic_runtime(runtime, sqlite_path=database)
    kinetic1.register_workflow(trigger_workflow())

    def start(runtime_instance):
        return runtime_instance.start_workflow(
            "trigger-once",
            subject=ObjectRef(id="K-201", type="Compressor"),
            actor_id="agent-1",
            actor_roles={"ai_agent_recommender"},
            trigger_key="sqlite-same-trigger",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(start, kinetic1)
        second = pool.submit(start, kinetic2)
        instances = [first.result(), second.result()]

    assert instances[0].id == instances[1].id
    events = [entry.event for entry in kinetic1.history(instances[0].id)]
    assert events.count("workflow_started") == 1

    kinetic1.repository.close()  # type: ignore[attr-defined]
    kinetic2.repository.close()  # type: ignore[attr-defined]


def test_invalid_resilience_policy_does_not_persist_definition():
    runtime = build_runtime()
    add_compressor(runtime)
    resilient = ResilientKineticRuntime(runtime)
    definition = trigger_workflow()

    with pytest.raises(ValueError, match="only supported for Function"):
        resilient.register_resilient_workflow(
            definition,
            step_policies={"approval": StepExecutionPolicy(max_attempts=2)},
        )

    assert resilient.repository.get_definition(definition.id, definition.version) is None


def test_resilience_policies_are_scoped_by_definition_version():
    runtime = build_runtime()
    add_compressor(runtime)
    resilient = ResilientKineticRuntime(runtime)

    v1 = WorkflowDefinition(
        id="resilience-versioned",
        name="Resilience versioned",
        version="1.0.0",
        steps=[
            WorkflowStepDefinition(
                id="risk",
                type=WorkflowStepType.function,
                operation="calculateAssetRisk",
                parameters={"asset_id": "${subject.id}"},
            )
        ],
    )
    v2 = v1.model_copy(deep=True)
    v2.version = "2.0.0"

    resilient.register_resilient_workflow(
        v1,
        step_policies={"risk": StepExecutionPolicy(max_attempts=2)},
    )
    resilient.register_resilient_workflow(
        v2,
        step_policies={"risk": StepExecutionPolicy(max_attempts=4)},
    )

    p1 = resilient.resilience_repository.get_step_policy(
        "resilience-versioned@1.0.0", "risk"
    )
    p2 = resilient.resilience_repository.get_step_policy(
        "resilience-versioned@2.0.0", "risk"
    )
    assert p1 is not None and p1.max_attempts == 2
    assert p2 is not None and p2.max_attempts == 4
