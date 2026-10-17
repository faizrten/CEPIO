from __future__ import annotations

from .workflow_policy import WorkflowPolicyApprovalPending

import sqlite3
from enum import Enum
from pathlib import Path
from threading import RLock
from time import monotonic, sleep
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .external_actions import (
    ExternalActionExecution,
    ExternalActionRuntime,
    ExternalActionStatus,
)
from .kinetic import (
    InMemoryWorkflowRepository,
    KineticRuntime,
    SQLiteWorkflowRepository,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepState,
    WorkflowStepStatus,
    WorkflowStepType,
)
from .kinetic_resilience import (
    InMemoryResilienceRepository,
    NonRetryableWorkflowError,
    ResilienceRepository,
    ResilientKineticRuntime,
    SQLiteResilienceRepository,
    WorkflowStepTimeout,
)
from .model import ObjectRef, utcnow
from .runtime import CEPIORuntime


class WorkflowOutcomeStatus(str, Enum):
    verified = "verified"
    failed = "failed"


class WorkflowOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_instance_id: str
    definition_id: str
    definition_version: str
    step_id: str
    subject: ObjectRef
    action_id: str
    external_execution_id: str
    status: WorkflowOutcomeStatus
    evidence: dict[str, Any] = Field(default_factory=dict)
    recorded_at: Any = Field(default_factory=utcnow)


class WorkflowOutcomeRepository(Protocol):
    def save_outcome(self, outcome: WorkflowOutcome) -> WorkflowOutcome: ...
    def get_outcome(self, outcome_id: str) -> WorkflowOutcome | None: ...
    def find_outcome_for_step(
        self, workflow_instance_id: str, step_id: str
    ) -> WorkflowOutcome | None: ...
    def list_outcomes(self, workflow_instance_id: str) -> list[WorkflowOutcome]: ...


def _outcome_semantics(outcome: WorkflowOutcome) -> dict[str, Any]:
    return outcome.model_dump(mode="json", exclude={"id", "recorded_at"})


class InMemoryWorkflowOutcomeRepository(WorkflowOutcomeRepository):
    def __init__(self) -> None:
        self._outcomes: dict[str, WorkflowOutcome] = {}
        self._by_step: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def save_outcome(self, outcome: WorkflowOutcome) -> WorkflowOutcome:
        key = (outcome.workflow_instance_id, outcome.step_id)
        with self._lock:
            prior_id = self._by_step.get(key)
            if prior_id is not None:
                prior = self._outcomes[prior_id]
                if _outcome_semantics(prior) != _outcome_semantics(outcome):
                    raise ValueError(
                        f"Workflow outcome for {outcome.workflow_instance_id}:{outcome.step_id} is immutable"
                    )
                return prior.model_copy(deep=True)
            self._outcomes[outcome.id] = outcome.model_copy(deep=True)
            self._by_step[key] = outcome.id
            return outcome.model_copy(deep=True)

    def get_outcome(self, outcome_id: str) -> WorkflowOutcome | None:
        with self._lock:
            item = self._outcomes.get(outcome_id)
            return item.model_copy(deep=True) if item else None

    def find_outcome_for_step(
        self, workflow_instance_id: str, step_id: str
    ) -> WorkflowOutcome | None:
        with self._lock:
            outcome_id = self._by_step.get((workflow_instance_id, step_id))
            item = self._outcomes.get(outcome_id) if outcome_id else None
            return item.model_copy(deep=True) if item else None

    def list_outcomes(self, workflow_instance_id: str) -> list[WorkflowOutcome]:
        with self._lock:
            values = [
                item.model_copy(deep=True)
                for item in self._outcomes.values()
                if item.workflow_instance_id == workflow_instance_id
            ]
            return sorted(values, key=lambda item: (str(item.recorded_at), item.id))


class SQLiteWorkflowOutcomeRepository(WorkflowOutcomeRepository):
    """Durable immutable workflow outcomes for external verification gates."""

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
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_outcomes (
                    id TEXT PRIMARY KEY,
                    workflow_instance_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(workflow_instance_id, step_id)
                );
                CREATE INDEX IF NOT EXISTS idx_workflow_outcomes_instance
                    ON workflow_outcomes(workflow_instance_id, recorded_at);
                """
            )
            self._conn.commit()

    def save_outcome(self, outcome: WorkflowOutcome) -> WorkflowOutcome:
        with self._lock:
            prior = self._conn.execute(
                """
                SELECT payload FROM workflow_outcomes
                WHERE workflow_instance_id = ? AND step_id = ?
                """,
                (outcome.workflow_instance_id, outcome.step_id),
            ).fetchone()
            if prior is not None:
                stored = WorkflowOutcome.model_validate_json(prior["payload"])
                if _outcome_semantics(stored) != _outcome_semantics(outcome):
                    raise ValueError(
                        f"Workflow outcome for {outcome.workflow_instance_id}:{outcome.step_id} is immutable"
                    )
                return stored
            try:
                self._conn.execute(
                    """
                    INSERT INTO workflow_outcomes(
                        id, workflow_instance_id, step_id, status, recorded_at, payload
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (
                        outcome.id,
                        outcome.workflow_instance_id,
                        outcome.step_id,
                        outcome.status.value,
                        outcome.recorded_at.isoformat(),
                        outcome.model_dump_json(),
                    ),
                )
                self._conn.commit()
                return outcome.model_copy(deep=True)
            except sqlite3.IntegrityError:
                self._conn.rollback()
                prior = self._conn.execute(
                    """
                    SELECT payload FROM workflow_outcomes
                    WHERE workflow_instance_id = ? AND step_id = ?
                    """,
                    (outcome.workflow_instance_id, outcome.step_id),
                ).fetchone()
                if prior is None:
                    raise
                stored = WorkflowOutcome.model_validate_json(prior["payload"])
                if _outcome_semantics(stored) != _outcome_semantics(outcome):
                    raise ValueError(
                        f"Workflow outcome for {outcome.workflow_instance_id}:{outcome.step_id} changed concurrently"
                    )
                return stored

    def get_outcome(self, outcome_id: str) -> WorkflowOutcome | None:
        row = self._conn.execute(
            "SELECT payload FROM workflow_outcomes WHERE id = ?", (outcome_id,)
        ).fetchone()
        return WorkflowOutcome.model_validate_json(row["payload"]) if row else None

    def find_outcome_for_step(
        self, workflow_instance_id: str, step_id: str
    ) -> WorkflowOutcome | None:
        row = self._conn.execute(
            """
            SELECT payload FROM workflow_outcomes
            WHERE workflow_instance_id = ? AND step_id = ?
            """,
            (workflow_instance_id, step_id),
        ).fetchone()
        return WorkflowOutcome.model_validate_json(row["payload"]) if row else None

    def list_outcomes(self, workflow_instance_id: str) -> list[WorkflowOutcome]:
        rows = self._conn.execute(
            """
            SELECT payload FROM workflow_outcomes
            WHERE workflow_instance_id = ?
            ORDER BY recorded_at, id
            """,
            (workflow_instance_id,),
        ).fetchall()
        return [WorkflowOutcome.model_validate_json(row["payload"]) for row in rows]


class _ExternalVerificationMixin:
    runtime: CEPIORuntime
    external_actions: ExternalActionRuntime
    outcome_repository: WorkflowOutcomeRepository

    def _configure_external_verification(
        self,
        external_actions: ExternalActionRuntime,
        outcome_repository: WorkflowOutcomeRepository | None,
    ) -> None:
        if external_actions.runtime is not self.runtime:
            raise ValueError(
                "Kinetic runtime and ExternalActionRuntime must share the same CEPIO runtime"
            )
        self.external_actions = external_actions
        self.outcome_repository = outcome_repository or InMemoryWorkflowOutcomeRepository()

    def outcome_for_step(self, instance_id: str, step_id: str) -> WorkflowOutcome | None:
        self.get_instance(instance_id)
        return self.outcome_repository.find_outcome_for_step(instance_id, step_id)

    def outcomes(self, instance_id: str) -> list[WorkflowOutcome]:
        self.get_instance(instance_id)
        return self.outcome_repository.list_outcomes(instance_id)

    def tick_external_verification(
        self,
        instance_id: str,
        *,
        reconcile_unknown: bool = False,
    ) -> WorkflowInstance:
        instance = self.get_instance(instance_id)
        if instance.status in {
            WorkflowStatus.completed,
            WorkflowStatus.failed,
            WorkflowStatus.cancelled,
        }:
            return instance
        if instance.status != WorkflowStatus.waiting_for_external_verification:
            raise RuntimeError(f"Workflow {instance.id} is not waiting for external verification")

        definition = self._definition(instance.definition_id, instance.definition_version)
        step = definition.steps[instance.current_step]
        if step.type != WorkflowStepType.external_verification:
            raise RuntimeError("Current workflow step is not an external verification gate")
        state = instance.step_states[step.id]
        if not state.external_execution_id:
            raise RuntimeError("External verification gate has no external execution")

        execution = self.external_actions.get_execution(state.external_execution_id)
        if execution.status == ExternalActionStatus.pending_execution:
            self.external_actions.dispatch(execution.id)
        elif execution.status in {
            ExternalActionStatus.acknowledged,
            ExternalActionStatus.pending_verification,
        }:
            self.external_actions.verify(execution.id)
        elif execution.status in {
            ExternalActionStatus.unknown,
            ExternalActionStatus.dispatching,
        }:
            if reconcile_unknown:
                self.external_actions.reconcile(execution.id)
        # Terminal states deliberately perform no adapter call.

        instance = self.get_instance(instance.id)
        if instance.status not in {
            WorkflowStatus.completed,
            WorkflowStatus.failed,
            WorkflowStatus.cancelled,
        }:
            instance.status = WorkflowStatus.running
            self.repository.save_instance(instance)
        return self._advance(instance)

    def _run_external_verification(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        state: WorkflowStepState,
    ) -> WorkflowInstance | None:
        if not step.action_step_id:
            raise RuntimeError(f"External verification step {step.id} has no action_step_id")
        action_state = instance.step_states.get(step.action_step_id)
        if action_state is None or not action_state.action_id:
            raise RuntimeError(
                f"External verification step {step.id} has no executed Action to verify"
            )

        execution: ExternalActionExecution
        if state.external_execution_id is None:
            execution = self.external_actions.enqueue_from_action(action_state.action_id)
            state.external_execution_id = execution.id
            self.repository.save_instance(instance)
            self._history(
                instance,
                "external_execution_linked",
                instance.last_actor_id,
                step_id=step.id,
                details={
                    "action_step_id": step.action_step_id,
                    "action_id": action_state.action_id,
                    "external_execution_id": execution.id,
                },
            )
        else:
            execution = self.external_actions.get_execution(state.external_execution_id)

        if execution.action_id != action_state.action_id:
            raise RuntimeError(
                "External execution Action lineage does not match the referenced workflow Action"
            )
        if execution.workflow_instance_id != instance.id:
            raise RuntimeError(
                "External execution workflow lineage does not match this workflow instance"
            )

        if execution.status == ExternalActionStatus.verified:
            outcome = self._record_outcome(instance, step, action_state.action_id, execution)
            state.outcome_id = outcome.id
            state.error = None
            state.result = {
                "action_id": action_state.action_id,
                "external_execution_id": execution.id,
                "external_status": execution.status.value,
                "outcome_id": outcome.id,
                "outcome_status": outcome.status.value,
            }
            instance.status = WorkflowStatus.running
            self.repository.save_instance(instance)
            return None

        if execution.status == ExternalActionStatus.failed:
            outcome = self._record_outcome(instance, step, action_state.action_id, execution)
            state.outcome_id = outcome.id
            state.status = WorkflowStepStatus.failed
            state.error = (
                execution.failure_reason
                or execution.message
                or "External source verification failed"
            )
            state.result = {
                "action_id": action_state.action_id,
                "external_execution_id": execution.id,
                "external_status": execution.status.value,
                "outcome_id": outcome.id,
                "outcome_status": outcome.status.value,
            }
            state.completed_at = utcnow()
            instance.status = WorkflowStatus.failed
            instance.completed_at = utcnow()
            self.repository.save_instance(instance)
            self._history(
                instance,
                "external_verification_failed",
                instance.last_actor_id,
                step_id=step.id,
                details={
                    "external_execution_id": execution.id,
                    "failure_reason": execution.failure_reason,
                    "outcome_id": outcome.id,
                },
            )
            return self.get_instance(instance.id)

        prior_status = None
        if isinstance(state.result, dict):
            prior_status = state.result.get("external_status")
        state.status = WorkflowStepStatus.waiting_for_external_verification
        state.result = {
            "action_id": action_state.action_id,
            "external_execution_id": execution.id,
            "external_status": execution.status.value,
        }
        instance.status = WorkflowStatus.waiting_for_external_verification
        self.repository.save_instance(instance)
        if prior_status != execution.status.value:
            self._history(
                instance,
                "external_verification_waiting",
                instance.last_actor_id,
                step_id=step.id,
                details={
                    "external_execution_id": execution.id,
                    "external_status": execution.status.value,
                },
            )
        return self.get_instance(instance.id)

    def _record_outcome(
        self,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        action_id: str,
        execution: ExternalActionExecution,
    ) -> WorkflowOutcome:
        prior = self.outcome_repository.find_outcome_for_step(instance.id, step.id)
        if prior is not None:
            return prior
        status = (
            WorkflowOutcomeStatus.verified
            if execution.status == ExternalActionStatus.verified
            else WorkflowOutcomeStatus.failed
        )
        outcome = WorkflowOutcome(
            workflow_instance_id=instance.id,
            definition_id=instance.definition_id,
            definition_version=instance.definition_version,
            step_id=step.id,
            subject=instance.subject,
            action_id=action_id,
            external_execution_id=execution.id,
            status=status,
            evidence={
                "policy_evidence": [
                    a.policy_evidence
                    for a in self.runtime.audits_for_action(action_id)
                    if a.policy_evidence
                ],
                "external_status": execution.status.value,
                "source_request_id": execution.source_request_id,
                "source_payload": dict(execution.source_payload),
                "message": execution.message,
                "failure_reason": execution.failure_reason,
                "verified_at": (
                    execution.verified_at.isoformat() if execution.verified_at is not None else None
                ),
                "system": execution.system,
                "operation": execution.operation,
            },
        )
        stored = self.outcome_repository.save_outcome(outcome)
        self._history(
            instance,
            "workflow_outcome_recorded",
            instance.last_actor_id,
            step_id=step.id,
            details={
                "outcome_id": stored.id,
                "outcome_status": stored.status.value,
                "external_execution_id": execution.id,
            },
        )
        return stored


class ExternalKineticRuntime(_ExternalVerificationMixin, KineticRuntime):
    """Kinetic runtime with durable, source-neutral external verification gates."""

    def __init__(
        self,
        runtime: CEPIORuntime,
        external_actions: ExternalActionRuntime,
        *,
        repository: Any | None = None,
        outcome_repository: WorkflowOutcomeRepository | None = None,
    ) -> None:
        KineticRuntime.__init__(self, runtime, repository=repository)
        self._configure_external_verification(external_actions, outcome_repository)


class ExternalResilientKineticRuntime(_ExternalVerificationMixin, ResilientKineticRuntime):
    """Resilient kinetic runtime plus external verification gates."""

    def __init__(
        self,
        runtime: CEPIORuntime,
        external_actions: ExternalActionRuntime,
        *,
        repository: Any | None = None,
        resilience_repository: ResilienceRepository | None = None,
        outcome_repository: WorkflowOutcomeRepository | None = None,
    ) -> None:
        ResilientKineticRuntime.__init__(
            self,
            runtime,
            repository=repository,
            resilience_repository=resilience_repository,
        )
        self._configure_external_verification(external_actions, outcome_repository)

    def _advance(self, instance: WorkflowInstance) -> WorkflowInstance:
        definition = self._definition(instance.definition_id, instance.definition_version)
        while instance.current_step < len(definition.steps):
            step = definition.steps[instance.current_step]
            state = instance.step_states[step.id]
            if state.status == WorkflowStepStatus.completed:
                instance.current_step += 1
                continue

            if step.type == WorkflowStepType.approval:
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
                return self._wait_for_approval(instance, step, state)

            if step.type == WorkflowStepType.external_verification:
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
                wait_result = self._run_external_verification(instance, step, state)
                if wait_result is not None:
                    return wait_result
                state.status = WorkflowStepStatus.completed
                state.completed_at = utcnow()
                instance.current_step += 1
                self.repository.save_instance(instance)
                self._history(
                    instance,
                    "step_completed",
                    instance.last_actor_id,
                    step_id=step.id,
                    details={"external_verification": True},
                )
                continue

            policy = self._policy(instance.definition_id, instance.definition_version, step)
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
                except WorkflowPolicyApprovalPending as exc:
                    resilience.attempts -= 1
                    self.resilience_repository.save_step_state(resilience)
                    return self._wait_for_policy_approval(instance, step, state, exc)
                except Exception as exc:
                    state.result = None
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


def build_external_kinetic_runtime(
    runtime: CEPIORuntime,
    external_actions: ExternalActionRuntime,
    *,
    sqlite_path: str | Path | None = None,
) -> ExternalKineticRuntime:
    if sqlite_path is None:
        workflow_repository = InMemoryWorkflowRepository()
        outcome_repository: WorkflowOutcomeRepository = InMemoryWorkflowOutcomeRepository()
    else:
        workflow_repository = SQLiteWorkflowRepository(sqlite_path)
        outcome_repository = SQLiteWorkflowOutcomeRepository(sqlite_path)
    return ExternalKineticRuntime(
        runtime,
        external_actions,
        repository=workflow_repository,
        outcome_repository=outcome_repository,
    )


def build_external_resilient_kinetic_runtime(
    runtime: CEPIORuntime,
    external_actions: ExternalActionRuntime,
    *,
    sqlite_path: str | Path | None = None,
) -> ExternalResilientKineticRuntime:
    if sqlite_path is None:
        workflow_repository = InMemoryWorkflowRepository()
        resilience_repository: ResilienceRepository = InMemoryResilienceRepository()
        outcome_repository: WorkflowOutcomeRepository = InMemoryWorkflowOutcomeRepository()
    else:
        workflow_repository = SQLiteWorkflowRepository(sqlite_path)
        resilience_repository = SQLiteResilienceRepository(sqlite_path)
        outcome_repository = SQLiteWorkflowOutcomeRepository(sqlite_path)
    return ExternalResilientKineticRuntime(
        runtime,
        external_actions,
        repository=workflow_repository,
        resilience_repository=resilience_repository,
        outcome_repository=outcome_repository,
    )
