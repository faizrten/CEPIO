from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path
from threading import RLock
from time import monotonic, sleep
from typing import Any, Protocol

from pydantic import BaseModel, Field

from .kinetic import (
    InMemoryWorkflowRepository,
    KineticRuntime,
    SQLiteWorkflowRepository,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepStatus,
    WorkflowStepType,
)
from .model import ActionRequest, ActionResult, ActionStatus, PolicyEffect, utcnow
from .runtime import AuthorizationError, CEPIORuntime


class CompensationStatus(str, Enum):
    not_required = "not_required"
    pending = "pending"
    completed = "completed"
    failed = "failed"


class StepExecutionPolicy(BaseModel):
    """Durable execution-resilience policy for one workflow step.

    In v0.2 retries and timeouts are intentionally limited to Function steps.
    Automatic Action retry remains blocked until external adapter idempotency and
    reconciliation from #57 are available.
    """

    max_attempts: int = Field(default=1, ge=1, le=20)
    timeout_seconds: float | None = Field(default=None, gt=0)
    retry_delay_seconds: float = Field(default=0.0, ge=0.0, le=60.0)
    compensate_on_terminal_failure: bool = True


class WorkflowControlPolicy(BaseModel):
    cancel_roles: set[str] = Field(default_factory=set)
    compensate_on_cancel: bool = True


class StepResilienceState(BaseModel):
    instance_id: str
    step_id: str
    attempts: int = 0
    last_error: str | None = None
    last_duration_seconds: float | None = None
    timed_out: bool = False
    compensated: bool = False
    compensation_result: dict[str, Any] | None = None
    updated_at: Any = Field(default_factory=utcnow)


class WorkflowResilienceState(BaseModel):
    instance_id: str
    cancellation_requested: bool = False
    cancellation_reason: str | None = None
    cancellation_actor_id: str | None = None
    compensation_status: CompensationStatus = CompensationStatus.not_required
    compensation_error: str | None = None
    updated_at: Any = Field(default_factory=utcnow)


class WorkflowStepTimeout(RuntimeError):
    pass


class NonRetryableWorkflowError(RuntimeError):
    pass


class ResilienceRepository(Protocol):
    def save_step_policy(
        self, definition_id: str, step_id: str, policy: StepExecutionPolicy
    ) -> StepExecutionPolicy: ...

    def get_step_policy(
        self, definition_id: str, step_id: str
    ) -> StepExecutionPolicy | None: ...

    def save_control_policy(
        self, definition_id: str, policy: WorkflowControlPolicy
    ) -> WorkflowControlPolicy: ...

    def get_control_policy(self, definition_id: str) -> WorkflowControlPolicy | None: ...

    def save_step_state(self, state: StepResilienceState) -> StepResilienceState: ...
    def get_step_state(self, instance_id: str, step_id: str) -> StepResilienceState | None: ...
    def save_instance_state(self, state: WorkflowResilienceState) -> WorkflowResilienceState: ...
    def get_instance_state(self, instance_id: str) -> WorkflowResilienceState | None: ...


class InMemoryResilienceRepository(ResilienceRepository):
    def __init__(self) -> None:
        self._step_policies: dict[tuple[str, str], StepExecutionPolicy] = {}
        self._control_policies: dict[str, WorkflowControlPolicy] = {}
        self._step_states: dict[tuple[str, str], StepResilienceState] = {}
        self._instance_states: dict[str, WorkflowResilienceState] = {}
        self._lock = RLock()

    def save_step_policy(
        self, definition_id: str, step_id: str, policy: StepExecutionPolicy
    ) -> StepExecutionPolicy:
        with self._lock:
            self._step_policies[(definition_id, step_id)] = policy.model_copy(deep=True)
            return policy.model_copy(deep=True)

    def get_step_policy(
        self, definition_id: str, step_id: str
    ) -> StepExecutionPolicy | None:
        item = self._step_policies.get((definition_id, step_id))
        return item.model_copy(deep=True) if item else None

    def save_control_policy(
        self, definition_id: str, policy: WorkflowControlPolicy
    ) -> WorkflowControlPolicy:
        with self._lock:
            self._control_policies[definition_id] = policy.model_copy(deep=True)
            return policy.model_copy(deep=True)

    def get_control_policy(self, definition_id: str) -> WorkflowControlPolicy | None:
        item = self._control_policies.get(definition_id)
        return item.model_copy(deep=True) if item else None

    def save_step_state(self, state: StepResilienceState) -> StepResilienceState:
        with self._lock:
            state.updated_at = utcnow()
            self._step_states[(state.instance_id, state.step_id)] = state.model_copy(deep=True)
            return state.model_copy(deep=True)

    def get_step_state(self, instance_id: str, step_id: str) -> StepResilienceState | None:
        item = self._step_states.get((instance_id, step_id))
        return item.model_copy(deep=True) if item else None

    def save_instance_state(self, state: WorkflowResilienceState) -> WorkflowResilienceState:
        with self._lock:
            state.updated_at = utcnow()
            self._instance_states[state.instance_id] = state.model_copy(deep=True)
            return state.model_copy(deep=True)

    def get_instance_state(self, instance_id: str) -> WorkflowResilienceState | None:
        item = self._instance_states.get(instance_id)
        return item.model_copy(deep=True) if item else None


class SQLiteResilienceRepository(ResilienceRepository):
    """Durable reference store for retry/cancellation/compensation state."""

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
            CREATE TABLE IF NOT EXISTS workflow_step_policies (
                definition_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY(definition_id, step_id)
            );
            CREATE TABLE IF NOT EXISTS workflow_control_policies (
                definition_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflow_resilience_steps (
                instance_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY(instance_id, step_id)
            );
            CREATE TABLE IF NOT EXISTS workflow_resilience_instances (
                instance_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def save_step_policy(
        self, definition_id: str, step_id: str, policy: StepExecutionPolicy
    ) -> StepExecutionPolicy:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workflow_step_policies(definition_id, step_id, payload)
                VALUES(?,?,?)
                ON CONFLICT(definition_id, step_id) DO UPDATE SET payload=excluded.payload
                """,
                (definition_id, step_id, policy.model_dump_json()),
            )
            self._conn.commit()
        return policy.model_copy(deep=True)

    def get_step_policy(
        self, definition_id: str, step_id: str
    ) -> StepExecutionPolicy | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_step_policies WHERE definition_id = ? AND step_id = ?",
            (definition_id, step_id),
        ).fetchone()
        return StepExecutionPolicy.model_validate_json(row["payload"]) if row else None

    def save_control_policy(
        self, definition_id: str, policy: WorkflowControlPolicy
    ) -> WorkflowControlPolicy:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workflow_control_policies(definition_id, payload) VALUES(?,?)
                ON CONFLICT(definition_id) DO UPDATE SET payload=excluded.payload
                """,
                (definition_id, policy.model_dump_json()),
            )
            self._conn.commit()
        return policy.model_copy(deep=True)

    def get_control_policy(self, definition_id: str) -> WorkflowControlPolicy | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_control_policies WHERE definition_id = ?",
            (definition_id,),
        ).fetchone()
        return WorkflowControlPolicy.model_validate_json(row["payload"]) if row else None

    def save_step_state(self, state: StepResilienceState) -> StepResilienceState:
        with self._lock:
            state.updated_at = utcnow()
            self._conn.execute(
                """
                INSERT INTO workflow_resilience_steps(instance_id, step_id, payload)
                VALUES(?,?,?)
                ON CONFLICT(instance_id, step_id) DO UPDATE SET payload=excluded.payload
                """,
                (state.instance_id, state.step_id, state.model_dump_json()),
            )
            self._conn.commit()
        return state.model_copy(deep=True)

    def get_step_state(self, instance_id: str, step_id: str) -> StepResilienceState | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_resilience_steps WHERE instance_id = ? AND step_id = ?",
            (instance_id, step_id),
        ).fetchone()
        return StepResilienceState.model_validate_json(row["payload"]) if row else None

    def save_instance_state(self, state: WorkflowResilienceState) -> WorkflowResilienceState:
        with self._lock:
            state.updated_at = utcnow()
            self._conn.execute(
                """
                INSERT INTO workflow_resilience_instances(instance_id, payload) VALUES(?,?)
                ON CONFLICT(instance_id) DO UPDATE SET payload=excluded.payload
                """,
                (state.instance_id, state.model_dump_json()),
            )
            self._conn.commit()
        return state.model_copy(deep=True)

    def get_instance_state(self, instance_id: str) -> WorkflowResilienceState | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_resilience_instances WHERE instance_id = ?",
            (instance_id,),
        ).fetchone()
        return WorkflowResilienceState.model_validate_json(row["payload"]) if row else None


class ResilientKineticRuntime(KineticRuntime):
    """Execution-resilient kinetic coordinator layered over the durable v0.1 kernel."""

    def __init__(
        self,
        runtime: CEPIORuntime,
        repository: Any | None = None,
        resilience_repository: ResilienceRepository | None = None,
    ) -> None:
        super().__init__(runtime, repository=repository)
        self.resilience_repository = resilience_repository or InMemoryResilienceRepository()

    def register_resilient_workflow(
        self,
        definition: WorkflowDefinition,
        *,
        step_policies: dict[str, StepExecutionPolicy] | None = None,
        control_policy: WorkflowControlPolicy | None = None,
    ) -> WorkflowDefinition:
        stored = super().register_workflow(definition)
        by_id = {step.id: step for step in definition.steps}
        for step_id, policy in (step_policies or {}).items():
            if step_id not in by_id:
                raise ValueError(f"Unknown workflow step for resilience policy: {step_id}")
            self._validate_execution_policy(by_id[step_id], policy)
            self.resilience_repository.save_step_policy(definition.id, step_id, policy)
        self.resilience_repository.save_control_policy(
            definition.id, control_policy or WorkflowControlPolicy()
        )
        return stored

    def step_resilience(self, instance_id: str, step_id: str) -> StepResilienceState:
        self.get_instance(instance_id)
        state = self.resilience_repository.get_step_state(instance_id, step_id)
        if state is None:
            state = StepResilienceState(instance_id=instance_id, step_id=step_id)
            self.resilience_repository.save_step_state(state)
        return state

    def resilience_state(self, instance_id: str) -> WorkflowResilienceState:
        self.get_instance(instance_id)
        state = self.resilience_repository.get_instance_state(instance_id)
        if state is None:
            state = WorkflowResilienceState(instance_id=instance_id)
            self.resilience_repository.save_instance_state(state)
        return state

    def cancel(
        self,
        instance_id: str,
        *,
        actor_id: str,
        actor_roles: set[str],
        reason: str | None = None,
        compensate: bool | None = None,
    ) -> WorkflowInstance:
        instance = self.get_instance(instance_id)
        if instance.status in {
            WorkflowStatus.completed,
            WorkflowStatus.failed,
            WorkflowStatus.cancelled,
        }:
            return instance

        self.runtime.read_object_for_actor(instance.subject.id, set(actor_roles))
        control = self.resilience_repository.get_control_policy(instance.definition_id) or WorkflowControlPolicy()
        allowed = actor_id == instance.initiated_by or bool(control.cancel_roles.intersection(actor_roles))
        if not allowed:
            raise PermissionError("Actor is not authorized to cancel this workflow")

        resilience = self.resilience_state(instance.id)
        resilience.cancellation_requested = True
        resilience.cancellation_reason = reason
        resilience.cancellation_actor_id = actor_id
        self.resilience_repository.save_instance_state(resilience)

        instance.last_actor_id = actor_id
        instance.last_actor_roles = set(actor_roles)
        self._history(
            instance,
            "workflow_cancellation_requested",
            actor_id,
            details={"reason": reason},
        )

        should_compensate = control.compensate_on_cancel if compensate is None else compensate
        if should_compensate:
            self._compensate_completed_actions(instance, actor_id, set(actor_roles))

        instance.status = WorkflowStatus.cancelled
        instance.completed_at = utcnow()
        self.repository.save_instance(instance)
        self._history(instance, "workflow_cancelled", actor_id, details={"reason": reason})
        return self.get_instance(instance.id)

    def _advance(self, instance: WorkflowInstance) -> WorkflowInstance:
        definition = self._definition(instance.definition_id)
        while instance.current_step < len(definition.steps):
            step = definition.steps[instance.current_step]
            state = instance.step_states[step.id]
            if state.status == WorkflowStepStatus.completed:
                instance.current_step += 1
                continue

            if step.type == WorkflowStepType.approval:
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
                return self._wait_for_approval(instance, step, state)

            policy = self._policy(instance.definition_id, step)
            state.status = WorkflowStepStatus.running
            state.started_at = state.started_at or utcnow()
            self.repository.save_instance(instance)
            self._history(
                instance,
                "step_started",
                instance.last_actor_id,
                step_id=step.id,
                details={"type": step.type.value, "max_attempts": policy.max_attempts},
            )

            resilience = self.step_resilience(instance.id, step.id)
            success = False
            while resilience.attempts < policy.max_attempts:
                resilience.attempts += 1
                resilience.last_error = None
                resilience.timed_out = False
                self.resilience_repository.save_step_state(resilience)
                self._history(
                    instance,
                    "step_attempt_started",
                    instance.last_actor_id,
                    step_id=step.id,
                    details={"attempt": resilience.attempts},
                )
                started = monotonic()
                try:
                    if step.type == WorkflowStepType.function:
                        self._run_function(instance, step, state)
                    elif step.type == WorkflowStepType.decision:
                        self._run_decision(instance, step, state)
                    elif step.type == WorkflowStepType.action:
                        self._run_governed_action(instance, step, state)
                    else:
                        raise NonRetryableWorkflowError(
                            f"Unsupported resilient workflow step type: {step.type}"
                        )

                    elapsed = monotonic() - started
                    resilience.last_duration_seconds = elapsed
                    if policy.timeout_seconds is not None and elapsed > policy.timeout_seconds:
                        resilience.timed_out = True
                        raise WorkflowStepTimeout(
                            f"Step {step.id} exceeded timeout of {policy.timeout_seconds}s "
                            f"(elapsed={elapsed:.6f}s)"
                        )
                    success = True
                    self.resilience_repository.save_step_state(resilience)
                    break
                except Exception as exc:
                    elapsed = monotonic() - started
                    resilience.last_duration_seconds = elapsed
                    resilience.last_error = str(exc)
                    if isinstance(exc, WorkflowStepTimeout):
                        resilience.timed_out = True
                    self.resilience_repository.save_step_state(resilience)

                    retryable = self._is_retryable(exc)
                    if retryable and resilience.attempts < policy.max_attempts:
                        self._history(
                            instance,
                            "step_retry_scheduled",
                            instance.last_actor_id,
                            step_id=step.id,
                            details={
                                "attempt": resilience.attempts,
                                "next_attempt": resilience.attempts + 1,
                                "error": str(exc),
                            },
                        )
                        if policy.retry_delay_seconds:
                            sleep(policy.retry_delay_seconds)
                        continue

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
                        details={
                            "error": str(exc),
                            "attempts": resilience.attempts,
                            "retryable": retryable,
                        },
                    )
                    if policy.compensate_on_terminal_failure:
                        self._compensate_completed_actions(
                            instance,
                            instance.last_actor_id,
                            set(instance.last_actor_roles),
                        )
                    return self.get_instance(instance.id)

            if not success:
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
                details={"attempts": resilience.attempts},
            )

        instance.status = WorkflowStatus.completed
        instance.completed_at = utcnow()
        self.repository.save_instance(instance)
        self._history(instance, "workflow_completed", instance.last_actor_id)
        return self.get_instance(instance.id)

    def _run_governed_action(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: Any,
    ) -> None:
        if step.operation is None:
            raise NonRetryableWorkflowError(f"Action step {step.id} has no operation")
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
        try:
            result = self.runtime.execute_action(request)
        except AuthorizationError as exc:
            raise NonRetryableWorkflowError(str(exc)) from exc
        if result.status == ActionStatus.rejected:
            raise NonRetryableWorkflowError(
                f"Action {step.operation} was rejected: {result.message}"
            )
        if result.status != ActionStatus.executed:
            raise RuntimeError(f"Action {step.operation} did not execute: {result.message}")
        state.action_id = result.action_id
        state.result = {
            "action_id": result.action_id,
            "audit_id": result.audit_id,
            "effects": result.effects,
            "replayed": result.replayed,
            "compensation": result.compensation,
        }

    def _compensate_completed_actions(
        self,
        instance: WorkflowInstance,
        actor_id: str,
        actor_roles: set[str],
    ) -> None:
        definition = self._definition(instance.definition_id)
        workflow_state = self.resilience_state(instance.id)
        candidates: list[tuple[WorkflowStepDefinition, Any]] = []
        for step in reversed(definition.steps[: instance.current_step + 1]):
            if step.type != WorkflowStepType.action:
                continue
            state = instance.step_states[step.id]
            if state.action_id and isinstance(state.result, dict):
                candidates.append((step, state))

        compensatable = []
        for step, state in candidates:
            definition_obj = self.runtime._actions.get(step.operation or "")
            if definition_obj and definition_obj.compensation_handler:
                compensatable.append((step, state, definition_obj))

        if not compensatable:
            workflow_state.compensation_status = CompensationStatus.not_required
            self.resilience_repository.save_instance_state(workflow_state)
            return

        workflow_state.compensation_status = CompensationStatus.pending
        workflow_state.compensation_error = None
        self.resilience_repository.save_instance_state(workflow_state)
        self._history(
            instance,
            "workflow_compensation_started",
            actor_id,
            details={"steps": [step.id for step, _, _ in compensatable]},
        )

        try:
            for step, state, action_definition in compensatable:
                step_resilience = self.step_resilience(instance.id, step.id)
                if step_resilience.compensated:
                    continue

                target = self.runtime.get_object(instance.subject.id)
                request = ActionRequest(
                    action_type=step.operation or "",
                    target=instance.subject,
                    actor_id=actor_id,
                    actor_roles=set(actor_roles),
                    parameters=self._resolve(step.parameters, instance),
                    idempotency_key=f"workflow:{instance.id}:compensate:{step.id}",
                    correlation_id=instance.id,
                    decision_id=self._latest_decision_id(instance),
                )
                policy = self.runtime.policy_engine.evaluate_action(
                    request, target, action_definition
                )
                if policy.effect != PolicyEffect.allow:
                    raise AuthorizationError(
                        "; ".join(policy.reasons) or "Compensation rejected by policy"
                    )

                scoped_key = self.runtime._scoped_idempotency_key(request)
                prior = (
                    self.runtime.audit_repository.get_idempotent_result(scoped_key)
                    if scoped_key
                    else None
                )
                if prior:
                    result = prior.model_copy(deep=True)
                    result.replayed = True
                    audit = self.runtime._audit(request, result, policy, replayed=True)
                    result.audit_id = audit.id
                else:
                    effects = action_definition.compensation_handler(
                        request,
                        target,
                        dict(state.result.get("effects", {})),
                        self.runtime,
                    )
                    result = ActionResult(
                        action_id=state.action_id,
                        action_type=step.operation or "",
                        target=instance.subject,
                        status=ActionStatus.compensated,
                        message="Action compensated",
                        effects=effects,
                        policy_reasons=policy.reasons,
                    )
                    audit = self.runtime._audit(request, result, policy)
                    result.audit_id = audit.id
                    self.runtime._cache_idempotent(scoped_key, result)

                step_resilience.compensated = True
                step_resilience.compensation_result = {
                    "action_id": result.action_id,
                    "audit_id": result.audit_id,
                    "effects": result.effects,
                    "replayed": result.replayed,
                }
                self.resilience_repository.save_step_state(step_resilience)
                self._history(
                    instance,
                    "step_compensated",
                    actor_id,
                    step_id=step.id,
                    details=step_resilience.compensation_result,
                )

            workflow_state.compensation_status = CompensationStatus.completed
            self.resilience_repository.save_instance_state(workflow_state)
            self._history(instance, "workflow_compensation_completed", actor_id)
        except Exception as exc:
            workflow_state.compensation_status = CompensationStatus.failed
            workflow_state.compensation_error = str(exc)
            self.resilience_repository.save_instance_state(workflow_state)
            self._history(
                instance,
                "workflow_compensation_failed",
                actor_id,
                details={"error": str(exc)},
            )

    def _policy(
        self, definition_id: str, step: WorkflowStepDefinition
    ) -> StepExecutionPolicy:
        policy = self.resilience_repository.get_step_policy(definition_id, step.id)
        policy = policy or StepExecutionPolicy()
        self._validate_execution_policy(step, policy)
        return policy

    @staticmethod
    def _validate_execution_policy(
        step: WorkflowStepDefinition, policy: StepExecutionPolicy
    ) -> None:
        if step.type != WorkflowStepType.function and (
            policy.max_attempts != 1 or policy.timeout_seconds is not None
        ):
            raise ValueError(
                f"Automatic retry/timeout is only supported for Function steps in kinetic v0.2; "
                f"step {step.id} is {step.type.value}"
            )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        return not isinstance(
            exc,
            (
                AuthorizationError,
                NonRetryableWorkflowError,
                PermissionError,
                KeyError,
                ValueError,
            ),
        )


def build_resilient_kinetic_runtime(
    runtime: CEPIORuntime,
    *,
    sqlite_path: str | Path | None = None,
) -> ResilientKineticRuntime:
    if sqlite_path is None:
        workflow_repository = InMemoryWorkflowRepository()
        resilience_repository: ResilienceRepository = InMemoryResilienceRepository()
    else:
        workflow_repository = SQLiteWorkflowRepository(sqlite_path)
        resilience_repository = SQLiteResilienceRepository(sqlite_path)
    return ResilientKineticRuntime(
        runtime,
        repository=workflow_repository,
        resilience_repository=resilience_repository,
    )
