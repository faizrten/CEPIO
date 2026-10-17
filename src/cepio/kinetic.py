from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .model import ActionRequest, Decision, ObjectRef, utcnow
from .runtime import CEPIORuntime


class WorkflowStepType(str, Enum):
    function = "function"
    decision = "decision"
    approval = "approval"
    action = "action"


class WorkflowStatus(str, Enum):
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class WorkflowStepStatus(str, Enum):
    pending = "pending"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    completed = "completed"
    failed = "failed"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class WorkflowStepDefinition(BaseModel):
    id: str
    type: WorkflowStepType
    operation: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    approval_roles: set[str] = Field(default_factory=set)
    approval_message: str | None = None
    decision_problem: str | None = None
    decision_recommendation: str | None = None
    recommended_action: str | None = None


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    steps: list[WorkflowStepDefinition]


class WorkflowStepState(BaseModel):
    step_id: str
    status: WorkflowStepStatus = WorkflowStepStatus.pending
    result: Any | None = None
    decision_id: str | None = None
    action_id: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkflowInstance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    definition_id: str
    definition_version: str
    subject: ObjectRef
    inputs: dict[str, Any] = Field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.running
    current_step: int = 0
    step_states: dict[str, WorkflowStepState] = Field(default_factory=dict)
    initiated_by: str
    initiated_roles: set[str] = Field(default_factory=set)
    last_actor_id: str
    last_actor_roles: set[str] = Field(default_factory=set)
    trigger_key: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class ApprovalTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_instance_id: str
    step_id: str
    required_roles: set[str] = Field(default_factory=set)
    message: str
    status: ApprovalStatus = ApprovalStatus.pending
    requested_at: datetime = Field(default_factory=utcnow)
    decided_at: datetime | None = None
    decided_by: str | None = None
    comment: str | None = None


class WorkflowHistoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_instance_id: str
    event: str
    actor_id: str
    step_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utcnow)


class WorkflowRepository(Protocol):
    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition: ...
    def get_definition(self, definition_id: str) -> WorkflowDefinition | None: ...
    def save_instance(self, instance: WorkflowInstance) -> WorkflowInstance: ...
    def get_instance(self, instance_id: str) -> WorkflowInstance | None: ...
    def find_instance_by_trigger(self, trigger_key: str) -> WorkflowInstance | None: ...
    def append_history(self, entry: WorkflowHistoryEntry) -> WorkflowHistoryEntry: ...
    def list_history(self, instance_id: str) -> list[WorkflowHistoryEntry]: ...
    def save_approval(self, task: ApprovalTask) -> ApprovalTask: ...
    def get_approval(self, approval_id: str) -> ApprovalTask | None: ...
    def pending_approval_for_step(self, instance_id: str, step_id: str) -> ApprovalTask | None: ...


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._instances: dict[str, WorkflowInstance] = {}
        self._trigger_index: dict[str, str] = {}
        self._history: list[WorkflowHistoryEntry] = []
        self._approvals: dict[str, ApprovalTask] = {}
        self._lock = RLock()

    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        with self._lock:
            self._definitions[definition.id] = definition.model_copy(deep=True)
            return definition.model_copy(deep=True)

    def get_definition(self, definition_id: str) -> WorkflowDefinition | None:
        item = self._definitions.get(definition_id)
        return item.model_copy(deep=True) if item else None

    def save_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        with self._lock:
            instance.updated_at = utcnow()
            self._instances[instance.id] = instance.model_copy(deep=True)
            if instance.trigger_key:
                self._trigger_index.setdefault(instance.trigger_key, instance.id)
            return instance.model_copy(deep=True)

    def get_instance(self, instance_id: str) -> WorkflowInstance | None:
        item = self._instances.get(instance_id)
        return item.model_copy(deep=True) if item else None

    def find_instance_by_trigger(self, trigger_key: str) -> WorkflowInstance | None:
        instance_id = self._trigger_index.get(trigger_key)
        return self.get_instance(instance_id) if instance_id else None

    def append_history(self, entry: WorkflowHistoryEntry) -> WorkflowHistoryEntry:
        self._history.append(entry)
        return entry

    def list_history(self, instance_id: str) -> list[WorkflowHistoryEntry]:
        return [entry for entry in self._history if entry.workflow_instance_id == instance_id]

    def save_approval(self, task: ApprovalTask) -> ApprovalTask:
        self._approvals[task.id] = task.model_copy(deep=True)
        return task.model_copy(deep=True)

    def get_approval(self, approval_id: str) -> ApprovalTask | None:
        task = self._approvals.get(approval_id)
        return task.model_copy(deep=True) if task else None

    def pending_approval_for_step(self, instance_id: str, step_id: str) -> ApprovalTask | None:
        for task in self._approvals.values():
            if (
                task.workflow_instance_id == instance_id
                and task.step_id == step_id
                and task.status == ApprovalStatus.pending
            ):
                return task.model_copy(deep=True)
        return None


class SQLiteWorkflowRepository(WorkflowRepository):
    """Durable reference persistence for kinetic workflow execution."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = RLock()
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workflow_definitions (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflow_instances (
                id TEXT PRIMARY KEY,
                definition_id TEXT NOT NULL,
                status TEXT NOT NULL,
                trigger_key TEXT UNIQUE,
                updated_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_instance_definition
                ON workflow_instances(definition_id);
            CREATE TABLE IF NOT EXISTS workflow_history (
                id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_history_instance
                ON workflow_history(instance_id, occurred_at);
            CREATE TABLE IF NOT EXISTS workflow_approvals (
                id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_approval_step
                ON workflow_approvals(instance_id, step_id, status);
            """
        )
        self._conn.commit()

    @staticmethod
    def _dump(model: BaseModel) -> str:
        return model.model_dump_json()

    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workflow_definitions(id, version, payload) VALUES(?,?,?)
                ON CONFLICT(id) DO UPDATE SET version=excluded.version, payload=excluded.payload
                """,
                (definition.id, definition.version, self._dump(definition)),
            )
            self._conn.commit()
        return definition.model_copy(deep=True)

    def get_definition(self, definition_id: str) -> WorkflowDefinition | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_definitions WHERE id = ?", (definition_id,)
        ).fetchone()
        return WorkflowDefinition.model_validate_json(row["payload"]) if row else None

    def save_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        with self._lock:
            instance.updated_at = utcnow()
            self._conn.execute(
                """
                INSERT INTO workflow_instances(id, definition_id, status, trigger_key, updated_at, payload)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    definition_id=excluded.definition_id,
                    status=excluded.status,
                    trigger_key=excluded.trigger_key,
                    updated_at=excluded.updated_at,
                    payload=excluded.payload
                """,
                (
                    instance.id,
                    instance.definition_id,
                    instance.status.value,
                    instance.trigger_key,
                    instance.updated_at.isoformat(),
                    self._dump(instance),
                ),
            )
            self._conn.commit()
        return instance.model_copy(deep=True)

    def get_instance(self, instance_id: str) -> WorkflowInstance | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_instances WHERE id = ?", (instance_id,)
        ).fetchone()
        return WorkflowInstance.model_validate_json(row["payload"]) if row else None

    def find_instance_by_trigger(self, trigger_key: str) -> WorkflowInstance | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_instances WHERE trigger_key = ?", (trigger_key,)
        ).fetchone()
        return WorkflowInstance.model_validate_json(row["payload"]) if row else None

    def append_history(self, entry: WorkflowHistoryEntry) -> WorkflowHistoryEntry:
        self._conn.execute(
            "INSERT INTO workflow_history(id, instance_id, occurred_at, payload) VALUES(?,?,?,?)",
            (
                entry.id,
                entry.workflow_instance_id,
                entry.occurred_at.isoformat(),
                self._dump(entry),
            ),
        )
        self._conn.commit()
        return entry

    def list_history(self, instance_id: str) -> list[WorkflowHistoryEntry]:
        rows = self._conn.execute(
            "SELECT payload FROM workflow_history WHERE instance_id = ? ORDER BY occurred_at, id",
            (instance_id,),
        ).fetchall()
        return [WorkflowHistoryEntry.model_validate_json(row["payload"]) for row in rows]

    def save_approval(self, task: ApprovalTask) -> ApprovalTask:
        self._conn.execute(
            """
            INSERT INTO workflow_approvals(id, instance_id, step_id, status, requested_at, payload)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET status=excluded.status, payload=excluded.payload
            """,
            (
                task.id,
                task.workflow_instance_id,
                task.step_id,
                task.status.value,
                task.requested_at.isoformat(),
                self._dump(task),
            ),
        )
        self._conn.commit()
        return task.model_copy(deep=True)

    def get_approval(self, approval_id: str) -> ApprovalTask | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_approvals WHERE id = ?", (approval_id,)
        ).fetchone()
        return ApprovalTask.model_validate_json(row["payload"]) if row else None

    def pending_approval_for_step(self, instance_id: str, step_id: str) -> ApprovalTask | None:
        row = self._conn.execute(
            """
            SELECT payload FROM workflow_approvals
            WHERE instance_id = ? AND step_id = ? AND status = ?
            ORDER BY requested_at DESC LIMIT 1
            """,
            (instance_id, step_id, ApprovalStatus.pending.value),
        ).fetchone()
        return ApprovalTask.model_validate_json(row["payload"]) if row else None


class KineticRuntime:
    """Minimal durable workflow coordinator over existing CEPIO functions, decisions and actions."""

    def __init__(self, runtime: CEPIORuntime, repository: WorkflowRepository | None = None) -> None:
        self.runtime = runtime
        self.repository = repository or InMemoryWorkflowRepository()

    def register_workflow(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        if not definition.steps:
            raise ValueError("Workflow must contain at least one step")
        ids = [step.id for step in definition.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Workflow step ids must be unique")
        for step in definition.steps:
            if step.type in {WorkflowStepType.function, WorkflowStepType.action} and not step.operation:
                raise ValueError(f"Step {step.id} requires an operation")
            if step.type == WorkflowStepType.approval and not step.approval_roles:
                raise ValueError(f"Approval step {step.id} requires at least one approval role")
            if step.type == WorkflowStepType.decision and not step.decision_recommendation:
                raise ValueError(f"Decision step {step.id} requires a recommendation")
        return self.repository.save_definition(definition)

    def start_workflow(
        self,
        definition_id: str,
        *,
        subject: ObjectRef,
        actor_id: str,
        actor_roles: set[str],
        inputs: dict[str, Any] | None = None,
        trigger_key: str | None = None,
    ) -> WorkflowInstance:
        if trigger_key:
            prior = self.repository.find_instance_by_trigger(trigger_key)
            if prior:
                return prior

        definition = self._definition(definition_id)
        target = self.runtime.read_object_for_actor(subject.id, set(actor_roles))
        if target.type != subject.type:
            raise ValueError(
                f"Workflow subject type mismatch for {subject.id}: {subject.type} != {target.type}"
            )

        instance = WorkflowInstance(
            definition_id=definition.id,
            definition_version=definition.version,
            subject=subject,
            inputs=inputs or {},
            step_states={
                step.id: WorkflowStepState(step_id=step.id) for step in definition.steps
            },
            initiated_by=actor_id,
            initiated_roles=set(actor_roles),
            last_actor_id=actor_id,
            last_actor_roles=set(actor_roles),
            trigger_key=trigger_key,
        )
        self.repository.save_instance(instance)
        self._history(instance, "workflow_started", actor_id)
        return self._advance(instance)

    def get_instance(self, instance_id: str) -> WorkflowInstance:
        instance = self.repository.get_instance(instance_id)
        if not instance:
            raise KeyError(f"Unknown workflow instance: {instance_id}")
        return instance

    def history(self, instance_id: str) -> list[WorkflowHistoryEntry]:
        self.get_instance(instance_id)
        return self.repository.list_history(instance_id)

    def pending_approval(self, instance_id: str) -> ApprovalTask | None:
        instance = self.get_instance(instance_id)
        if instance.status != WorkflowStatus.waiting_for_approval:
            return None
        definition = self._definition(instance.definition_id)
        step = definition.steps[instance.current_step]
        return self.repository.pending_approval_for_step(instance.id, step.id)

    def decide_approval(
        self,
        approval_id: str,
        *,
        actor_id: str,
        actor_roles: set[str],
        approved: bool,
        comment: str | None = None,
    ) -> WorkflowInstance:
        task = self.repository.get_approval(approval_id)
        if not task:
            raise KeyError(f"Unknown workflow approval: {approval_id}")
        if task.status != ApprovalStatus.pending:
            return self.get_instance(task.workflow_instance_id)
        if task.required_roles and not task.required_roles.intersection(actor_roles):
            raise PermissionError(
                f"Actor lacks required approval role; requires one of {sorted(task.required_roles)}"
            )

        instance = self.get_instance(task.workflow_instance_id)
        if instance.status != WorkflowStatus.waiting_for_approval:
            raise RuntimeError("Workflow is not waiting for approval")

        task.status = ApprovalStatus.approved if approved else ApprovalStatus.rejected
        task.decided_at = utcnow()
        task.decided_by = actor_id
        task.comment = comment
        self.repository.save_approval(task)

        step_state = instance.step_states[task.step_id]
        instance.last_actor_id = actor_id
        instance.last_actor_roles = set(actor_roles)
        if not approved:
            step_state.status = WorkflowStepStatus.failed
            step_state.error = "Approval rejected"
            step_state.completed_at = utcnow()
            instance.status = WorkflowStatus.failed
            self.repository.save_instance(instance)
            self._history(
                instance,
                "approval_rejected",
                actor_id,
                step_id=task.step_id,
                details={"approval_id": task.id, "comment": comment},
            )
            return self.get_instance(instance.id)

        step_state.status = WorkflowStepStatus.completed
        step_state.result = {"approval_id": task.id, "approved_by": actor_id}
        step_state.completed_at = utcnow()
        instance.current_step += 1
        instance.status = WorkflowStatus.running
        self.repository.save_instance(instance)
        self._history(
            instance,
            "approval_granted",
            actor_id,
            step_id=task.step_id,
            details={"approval_id": task.id, "comment": comment},
        )
        return self._advance(instance)

    def resume(self, instance_id: str) -> WorkflowInstance:
        instance = self.get_instance(instance_id)
        if instance.status == WorkflowStatus.waiting_for_approval:
            return instance
        if instance.status in {WorkflowStatus.completed, WorkflowStatus.failed, WorkflowStatus.cancelled}:
            return instance
        return self._advance(instance)

    def _advance(self, instance: WorkflowInstance) -> WorkflowInstance:
        definition = self._definition(instance.definition_id)
        while instance.current_step < len(definition.steps):
            step = definition.steps[instance.current_step]
            state = instance.step_states[step.id]
            if state.status == WorkflowStepStatus.completed:
                instance.current_step += 1
                continue
            state.status = WorkflowStepStatus.running
            state.started_at = state.started_at or utcnow()
            self.repository.save_instance(instance)
            self._history(
                instance,
                "step_started",
                instance.last_actor_id,
                step_id=step.id,
                details={"type": step.type.value},
            )
            try:
                if step.type == WorkflowStepType.function:
                    self._run_function(instance, step, state)
                elif step.type == WorkflowStepType.decision:
                    self._run_decision(instance, step, state)
                elif step.type == WorkflowStepType.approval:
                    return self._wait_for_approval(instance, step, state)
                elif step.type == WorkflowStepType.action:
                    self._run_action(instance, step, state)
                else:
                    raise ValueError(f"Unsupported workflow step type: {step.type}")
            except Exception as exc:
                state.status = WorkflowStepStatus.failed
                state.error = str(exc)
                state.completed_at = utcnow()
                instance.status = WorkflowStatus.failed
                self.repository.save_instance(instance)
                self._history(
                    instance,
                    "step_failed",
                    instance.last_actor_id,
                    step_id=step.id,
                    details={"error": str(exc)},
                )
                return self.get_instance(instance.id)

            state.status = WorkflowStepStatus.completed
            state.completed_at = utcnow()
            instance.current_step += 1
            self.repository.save_instance(instance)
            self._history(
                instance,
                "step_completed",
                instance.last_actor_id,
                step_id=step.id,
            )

        instance.status = WorkflowStatus.completed
        instance.completed_at = utcnow()
        self.repository.save_instance(instance)
        self._history(instance, "workflow_completed", instance.last_actor_id)
        return self.get_instance(instance.id)

    def _run_function(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
    ) -> None:
        assert step.operation is not None
        if not self.runtime.policy_engine.can_call_function(
            instance.last_actor_roles, step.operation
        ):
            raise PermissionError(
                f"Actor roles are not authorized to call function {step.operation}"
            )
        arguments = self._resolve(step.parameters, instance)
        state.result = self.runtime.call_function(step.operation, **arguments)

    def _run_decision(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
    ) -> None:
        decision = Decision(
            subject=instance.subject,
            problem=step.decision_problem or f"Workflow decision at step {step.id}",
            observations=self._decision_observations(instance),
            recommendation=step.decision_recommendation or "",
            recommended_action=step.recommended_action,
            created_by=instance.last_actor_id,
        )
        stored = self.runtime.save_decision(decision)
        state.decision_id = stored.id
        state.result = {"decision_id": stored.id, "recommendation": stored.recommendation}

    def _wait_for_approval(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
    ) -> WorkflowInstance:
        task = self.repository.pending_approval_for_step(instance.id, step.id)
        if task is None:
            task = ApprovalTask(
                workflow_instance_id=instance.id,
                step_id=step.id,
                required_roles=set(step.approval_roles),
                message=step.approval_message or f"Approval required for workflow step {step.id}",
            )
            self.repository.save_approval(task)
            self._history(
                instance,
                "approval_requested",
                instance.last_actor_id,
                step_id=step.id,
                details={"approval_id": task.id, "required_roles": sorted(task.required_roles)},
            )
        state.status = WorkflowStepStatus.waiting_for_approval
        state.result = {"approval_id": task.id}
        instance.status = WorkflowStatus.waiting_for_approval
        self.repository.save_instance(instance)
        return self.get_instance(instance.id)

    def _run_action(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
    ) -> None:
        assert step.operation is not None
        request = ActionRequest(
            action_type=step.operation,
            target=instance.subject,
            actor_id=instance.last_actor_id,
            actor_roles=set(instance.last_actor_roles),
            parameters=self._resolve(step.parameters, instance),
            idempotency_key=f"workflow:{instance.id}:step:{step.id}",
            correlation_id=instance.id,
            decision_id=self._latest_decision_id(instance),
        )
        result = self.runtime.execute_action(request)
        if result.status.value != "executed":
            raise RuntimeError(f"Action {step.operation} did not execute: {result.message}")
        state.action_id = result.action_id
        state.result = {
            "action_id": result.action_id,
            "audit_id": result.audit_id,
            "effects": result.effects,
            "replayed": result.replayed,
        }

    def _definition(self, definition_id: str) -> WorkflowDefinition:
        definition = self.repository.get_definition(definition_id)
        if not definition:
            raise KeyError(f"Unknown workflow definition: {definition_id}")
        return definition

    def _history(
        self,
        instance: WorkflowInstance,
        event: str,
        actor_id: str,
        *,
        step_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.repository.append_history(
            WorkflowHistoryEntry(
                workflow_instance_id=instance.id,
                event=event,
                actor_id=actor_id,
                step_id=step_id,
                details=details or {},
            )
        )

    def _latest_decision_id(self, instance: WorkflowInstance) -> str | None:
        definition = self._definition(instance.definition_id)
        for step in reversed(definition.steps[: instance.current_step + 1]):
            decision_id = instance.step_states[step.id].decision_id
            if decision_id:
                return decision_id
        return None

    def _decision_observations(self, instance: WorkflowInstance) -> list[str]:
        definition = self._definition(instance.definition_id)
        observations: list[str] = []
        for step in definition.steps[: instance.current_step]:
            result = instance.step_states[step.id].result
            if result is not None:
                observations.append(f"{step.id}={json.dumps(result, default=str, sort_keys=True)}")
        return observations

    def _resolve(self, value: Any, instance: WorkflowInstance) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve(item, instance) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve(item, instance) for item in value]
        if not isinstance(value, str) or not (value.startswith("${") and value.endswith("}")):
            return value

        expression = value[2:-1]
        if expression == "subject.id":
            return instance.subject.id
        if expression == "subject.type":
            return instance.subject.type
        if expression.startswith("input."):
            key = expression.removeprefix("input.")
            if key not in instance.inputs:
                raise KeyError(f"Unknown workflow input: {key}")
            return instance.inputs[key]
        if expression.startswith("step."):
            _, step_id, *path = expression.split(".")
            if step_id not in instance.step_states:
                raise KeyError(f"Unknown workflow step reference: {step_id}")
            result: Any = instance.step_states[step_id].result
            for part in path:
                if not isinstance(result, dict) or part not in result:
                    raise KeyError(f"Unknown workflow result reference: {expression}")
                result = result[part]
            return result
        raise KeyError(f"Unsupported workflow expression: {expression}")
