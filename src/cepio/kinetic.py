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
from .model import ActionResult
from .contextual_policy import PolicyReference
from .workflow_policy import WorkflowPolicyApprovalPending, WorkflowPolicyBoundary
from .runtime import CEPIORuntime


class WorkflowStepType(str, Enum):
    function = "function"
    decision = "decision"
    approval = "approval"
    action = "action"
    external_verification = "external_verification"


class WorkflowStatus(str, Enum):
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    waiting_for_external_verification = "waiting_for_external_verification"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class WorkflowStepStatus(str, Enum):
    pending = "pending"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    waiting_for_external_verification = "waiting_for_external_verification"
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
    action_step_id: str | None = None


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    steps: list[WorkflowStepDefinition]
    policy_references: tuple[PolicyReference, ...] = Field(default=(), frozen=True)


class WorkflowStepState(BaseModel):
    step_id: str
    status: WorkflowStepStatus = WorkflowStepStatus.pending
    result: Any | None = None
    decision_id: str | None = None
    action_id: str | None = None
    policy_approval_id: str | None = None
    external_execution_id: str | None = None
    outcome_id: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkflowInstance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    definition_id: str
    definition_version: str
    policy_references: tuple[PolicyReference, ...] = Field(default=(), frozen=True)
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
    policy_fingerprint: str | None = None
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
    def get_definition(
        self, definition_id: str, version: str | None = None
    ) -> WorkflowDefinition | None: ...
    def create_instance_if_absent(
        self, instance: WorkflowInstance
    ) -> tuple[WorkflowInstance, bool]: ...
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
        self._definitions: dict[tuple[str, str], WorkflowDefinition] = {}
        self._definition_order: dict[str, list[str]] = {}
        self._instances: dict[str, WorkflowInstance] = {}
        self._trigger_index: dict[str, str] = {}
        self._history: list[WorkflowHistoryEntry] = []
        self._approvals: dict[str, ApprovalTask] = {}
        self._lock = RLock()

    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        key = (definition.id, definition.version)
        with self._lock:
            prior = self._definitions.get(key)
            if prior is not None:
                if prior.model_dump(mode="json") != definition.model_dump(mode="json"):
                    raise ValueError(
                        f"Workflow definition {definition.id}@{definition.version} is immutable"
                    )
                return prior.model_copy(deep=True)
            self._definitions[key] = definition.model_copy(deep=True)
            self._definition_order.setdefault(definition.id, []).append(definition.version)
            return definition.model_copy(deep=True)

    def get_definition(
        self, definition_id: str, version: str | None = None
    ) -> WorkflowDefinition | None:
        with self._lock:
            if version is None:
                versions = self._definition_order.get(definition_id, [])
                if not versions:
                    return None
                version = versions[-1]
            item = self._definitions.get((definition_id, version))
            return item.model_copy(deep=True) if item else None

    def create_instance_if_absent(
        self, instance: WorkflowInstance
    ) -> tuple[WorkflowInstance, bool]:
        with self._lock:
            if instance.trigger_key:
                prior_id = self._trigger_index.get(instance.trigger_key)
                if prior_id is not None:
                    return self._instances[prior_id].model_copy(deep=True), False
            instance.updated_at = utcnow()
            self._instances[instance.id] = instance.model_copy(deep=True)
            if instance.trigger_key:
                self._trigger_index[instance.trigger_key] = instance.id
            return instance.model_copy(deep=True), True

    def save_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        with self._lock:
            if instance.trigger_key:
                prior_id = self._trigger_index.get(instance.trigger_key)
                if prior_id is not None and prior_id != instance.id:
                    raise ValueError("Workflow trigger key already belongs to another instance")
                self._trigger_index[instance.trigger_key] = instance.id
            instance.updated_at = utcnow()
            self._instances[instance.id] = instance.model_copy(deep=True)
            return instance.model_copy(deep=True)

    def get_instance(self, instance_id: str) -> WorkflowInstance | None:
        with self._lock:
            item = self._instances.get(instance_id)
            return item.model_copy(deep=True) if item else None

    def find_instance_by_trigger(self, trigger_key: str) -> WorkflowInstance | None:
        with self._lock:
            instance_id = self._trigger_index.get(trigger_key)
            item = self._instances.get(instance_id) if instance_id else None
            return item.model_copy(deep=True) if item else None

    def append_history(self, entry: WorkflowHistoryEntry) -> WorkflowHistoryEntry:
        with self._lock:
            self._history.append(entry.model_copy(deep=True))
            return entry.model_copy(deep=True)

    def list_history(self, instance_id: str) -> list[WorkflowHistoryEntry]:
        with self._lock:
            return [
                entry.model_copy(deep=True)
                for entry in self._history
                if entry.workflow_instance_id == instance_id
            ]

    def save_approval(self, task: ApprovalTask) -> ApprovalTask:
        with self._lock:
            self._approvals[task.id] = task.model_copy(deep=True)
            return task.model_copy(deep=True)

    def get_approval(self, approval_id: str) -> ApprovalTask | None:
        with self._lock:
            task = self._approvals.get(approval_id)
            return task.model_copy(deep=True) if task else None

    def pending_approval_for_step(self, instance_id: str, step_id: str) -> ApprovalTask | None:
        with self._lock:
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
        with self._lock:
            existing = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_definitions'"
            ).fetchone()
            if existing is not None:
                info = self._conn.execute("PRAGMA table_info(workflow_definitions)").fetchall()
                pk_columns = [row["name"] for row in info if row["pk"]]
                if pk_columns == ["id"]:
                    self._conn.execute(
                        "ALTER TABLE workflow_definitions RENAME TO workflow_definitions_legacy_v030"
                    )
                    self._conn.execute(
                        """
                        CREATE TABLE workflow_definitions (
                            id TEXT NOT NULL,
                            version TEXT NOT NULL,
                            payload TEXT NOT NULL,
                            PRIMARY KEY(id, version)
                        )
                        """
                    )
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO workflow_definitions(id, version, payload)
                        SELECT id, version, payload FROM workflow_definitions_legacy_v030
                        """
                    )
                    self._conn.execute("DROP TABLE workflow_definitions_legacy_v030")
            else:
                self._conn.execute(
                    """
                    CREATE TABLE workflow_definitions (
                        id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY(id, version)
                    )
                    """
                )

            self._conn.executescript(
                """
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
        payload = self._dump(definition)
        with self._lock:
            prior = self._conn.execute(
                "SELECT payload FROM workflow_definitions WHERE id = ? AND version = ?",
                (definition.id, definition.version),
            ).fetchone()
            if prior is not None:
                prior_definition = WorkflowDefinition.model_validate_json(prior["payload"])
                if prior_definition.model_dump(mode="json") != definition.model_dump(mode="json"):
                    raise ValueError(
                        f"Workflow definition {definition.id}@{definition.version} is immutable"
                    )
                return prior_definition
            self._conn.execute(
                "INSERT INTO workflow_definitions(id, version, payload) VALUES(?,?,?)",
                (definition.id, definition.version, payload),
            )
            self._conn.commit()
        return definition.model_copy(deep=True)

    def get_definition(
        self, definition_id: str, version: str | None = None
    ) -> WorkflowDefinition | None:
        if version is not None:
            row = self._conn.execute(
                "SELECT payload FROM workflow_definitions WHERE id = ? AND version = ?",
                (definition_id, version),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT payload FROM workflow_definitions WHERE id = ? ORDER BY rowid DESC LIMIT 1",
                (definition_id,),
            ).fetchone()
        return WorkflowDefinition.model_validate_json(row["payload"]) if row else None

    def create_instance_if_absent(
        self, instance: WorkflowInstance
    ) -> tuple[WorkflowInstance, bool]:
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if instance.trigger_key:
                    prior = self._conn.execute(
                        "SELECT payload FROM workflow_instances WHERE trigger_key = ?",
                        (instance.trigger_key,),
                    ).fetchone()
                    if prior is not None:
                        self._conn.commit()
                        return WorkflowInstance.model_validate_json(prior["payload"]), False
                instance.updated_at = utcnow()
                self._conn.execute(
                    """
                    INSERT INTO workflow_instances(
                        id, definition_id, status, trigger_key, updated_at, payload
                    ) VALUES(?,?,?,?,?,?)
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
                return instance.model_copy(deep=True), True
            except sqlite3.IntegrityError:
                self._conn.rollback()
                if not instance.trigger_key:
                    raise
                prior = self._conn.execute(
                    "SELECT payload FROM workflow_instances WHERE trigger_key = ?",
                    (instance.trigger_key,),
                ).fetchone()
                if prior is None:
                    raise
                return WorkflowInstance.model_validate_json(prior["payload"]), False
            except Exception:
                self._conn.rollback()
                raise

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
        with self._lock:
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
        with self._lock:
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
        self.workflow_policy: WorkflowPolicyBoundary | None = None

    def register_workflow(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        self._validate_definition(definition)
        return self.repository.save_definition(definition)

    def _validate_definition(self, definition: WorkflowDefinition) -> None:
        if not definition.steps:
            raise ValueError("Workflow must contain at least one step")
        ids = [step.id for step in definition.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Workflow step ids must be unique")
        prior_by_id: dict[str, WorkflowStepDefinition] = {}
        for step in definition.steps:
            if (
                step.type in {WorkflowStepType.function, WorkflowStepType.action}
                and not step.operation
            ):
                raise ValueError(f"Step {step.id} requires an operation")
            if step.type == WorkflowStepType.approval and not step.approval_roles:
                raise ValueError(f"Approval step {step.id} requires at least one approval role")
            if step.type == WorkflowStepType.decision and not step.decision_recommendation:
                raise ValueError(f"Decision step {step.id} requires a recommendation")
            if step.type == WorkflowStepType.external_verification:
                if step.operation is not None:
                    raise ValueError(
                        f"External verification step {step.id} must not name a source operation"
                    )
                if not step.action_step_id:
                    raise ValueError(
                        f"External verification step {step.id} requires action_step_id"
                    )
                referenced = prior_by_id.get(step.action_step_id)
                if referenced is None or referenced.type != WorkflowStepType.action:
                    raise ValueError(
                        f"External verification step {step.id} must reference an earlier Action step"
                    )
            elif step.action_step_id is not None:
                raise ValueError(
                    f"Step {step.id} may only set action_step_id for external verification"
                )
            prior_by_id[step.id] = step

    def start_workflow(
        self,
        definition_id: str,
        *,
        subject: ObjectRef,
        actor_id: str,
        actor_roles: set[str],
        inputs: dict[str, Any] | None = None,
        trigger_key: str | None = None,
        definition_version: str | None = None,
    ) -> WorkflowInstance:
        definition = self._definition(definition_id, definition_version)
        target = self.runtime.read_object_for_actor(subject.id, set(actor_roles))
        if target.type != subject.type:
            raise ValueError(
                f"Workflow subject type mismatch for {subject.id}: {subject.type} != {target.type}"
            )

        candidate = WorkflowInstance(
            definition_id=definition.id,
            definition_version=definition.version,
            policy_references=definition.policy_references,
            subject=subject,
            inputs=inputs or {},
            step_states={step.id: WorkflowStepState(step_id=step.id) for step in definition.steps},
            initiated_by=actor_id,
            initiated_roles=set(actor_roles),
            last_actor_id=actor_id,
            last_actor_roles=set(actor_roles),
            trigger_key=trigger_key,
        )
        instance, created = self.repository.create_instance_if_absent(candidate)
        if not created:
            return instance
        self._history(
            instance,
            "workflow_started",
            actor_id,
            details={
                "definition_version": instance.definition_version,
                "policy_references": [
                    r.model_dump(mode="json") for r in instance.policy_references
                ],
            },
        )
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
        definition = self._definition(instance.definition_id, instance.definition_version)
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
        if task.policy_fingerprint and any(
            r.startswith("ai_") or "agent" in r for r in actor_roles
        ):
            raise PermissionError("AI roles cannot grant workflow policy approval")
        if (
            task.required_roles
            and not task.required_roles.issubset(actor_roles)
            and task.policy_fingerprint
        ):
            raise PermissionError("Actor lacks required policy approval roles")
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

        definition = self._definition(instance.definition_id, instance.definition_version)
        policy_approval = definition.steps[instance.current_step].type == WorkflowStepType.action
        step_state.status = (
            WorkflowStepStatus.pending if policy_approval else WorkflowStepStatus.completed
        )
        step_state.result = {"approval_id": task.id, "approved_by": actor_id}
        step_state.completed_at = utcnow()
        if not policy_approval:
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
        if instance.status in {
            WorkflowStatus.waiting_for_approval,
            WorkflowStatus.waiting_for_external_verification,
        }:
            return instance
        if instance.status in {
            WorkflowStatus.completed,
            WorkflowStatus.failed,
            WorkflowStatus.cancelled,
        }:
            return instance
        return self._advance(instance)

    def _advance(self, instance: WorkflowInstance) -> WorkflowInstance:
        definition = self._definition(instance.definition_id, instance.definition_version)
        while instance.current_step < len(definition.steps):
            step = definition.steps[instance.current_step]
            state = instance.step_states[step.id]
            if state.status == WorkflowStepStatus.completed:
                instance.current_step += 1
                continue
            first_start = state.started_at is None
            state.status = WorkflowStepStatus.running
            state.started_at = state.started_at or utcnow()
            self.repository.save_instance(instance)
            if first_start:
                self._history(
                    instance,
                    "step_started",
                    instance.last_actor_id,
                    step_id=step.id,
                    details={"type": step.type.value},
                )
            try:
                wait_result: WorkflowInstance | None = None
                if step.type == WorkflowStepType.function:
                    self._run_function(instance, step, state)
                elif step.type == WorkflowStepType.decision:
                    self._run_decision(instance, step, state)
                elif step.type == WorkflowStepType.approval:
                    return self._wait_for_approval(instance, step, state)
                elif step.type == WorkflowStepType.action:
                    self._run_action(instance, step, state)
                elif step.type == WorkflowStepType.external_verification:
                    wait_result = self._run_external_verification(instance, step, state)
                    if wait_result is not None:
                        return wait_result
                else:
                    raise ValueError(f"Unsupported workflow step type: {step.type}")
            except WorkflowPolicyApprovalPending as exc:
                return self._wait_for_policy_approval(instance, step, state, exc)
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
        state.result = {
            "decision_id": stored.id,
            "recommendation": stored.recommendation,
        }

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
                details={
                    "approval_id": task.id,
                    "required_roles": sorted(task.required_roles),
                },
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
            workflow_instance_id=instance.id,
            decision_id=self._latest_decision_id(instance),
        )
        result = self._execute_workflow_action(instance, step, request)
        if result.status.value != "executed":
            raise RuntimeError(f"Action {step.operation} did not execute: {result.message}")
        state.action_id = result.action_id
        state.result = {
            "action_id": result.action_id,
            "audit_id": result.audit_id,
            "effects": result.effects,
            "replayed": result.replayed,
        }

    def _execute_workflow_action(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        request: ActionRequest,
    ) -> ActionResult:
        definition = self._definition(instance.definition_id, instance.definition_version)
        if instance.policy_references != definition.policy_references:
            raise PermissionError("Workflow policy pins differ from immutable definition")
        if not instance.policy_references:
            return self.runtime.execute_action(request)
        if self.workflow_policy is None:
            raise PermissionError("Pinned workflow policies require a configured policy boundary")
        return self.workflow_policy.execute(self, instance, step, request)

    def _wait_for_policy_approval(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
        pending: WorkflowPolicyApprovalPending,
    ) -> WorkflowInstance:
        task = ApprovalTask(
            workflow_instance_id=instance.id,
            step_id=step.id,
            required_roles=pending.roles,
            message="Contextual policy requires human approval",
            policy_fingerprint=pending.fingerprint,
        )
        self.repository.save_approval(task)
        state.policy_approval_id = task.id
        self._history(
            instance,
            "policy_approval_requested",
            instance.last_actor_id,
            step_id=step.id,
            details={"approval_id": task.id, "policy_fingerprint": pending.fingerprint},
        )
        state.status = WorkflowStepStatus.waiting_for_approval
        state.result = {"approval_id": task.id}
        instance.status = WorkflowStatus.waiting_for_approval
        self.repository.save_instance(instance)
        return self.get_instance(instance.id)

    def _run_external_verification(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
    ) -> WorkflowInstance | None:
        raise RuntimeError(
            "External verification step requires an external-action-aware kinetic runtime"
        )

    def _definition(self, definition_id: str, version: str | None = None) -> WorkflowDefinition:
        definition = self.repository.get_definition(definition_id, version)
        if not definition:
            suffix = f"@{version}" if version is not None else ""
            raise KeyError(f"Unknown workflow definition: {definition_id}{suffix}")
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
        definition = self._definition(instance.definition_id, instance.definition_version)
        for step in reversed(definition.steps[: instance.current_step + 1]):
            decision_id = instance.step_states[step.id].decision_id
            if decision_id:
                return decision_id
        return None

    def _decision_observations(self, instance: WorkflowInstance) -> list[str]:
        definition = self._definition(instance.definition_id, instance.definition_version)
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
