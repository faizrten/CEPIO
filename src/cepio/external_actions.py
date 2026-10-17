from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .adapters import (
    AdapterVerificationStatus,
    GovernedVerificationRequest,
    GovernedVerificationResult,
    GovernedWriteAdapter,
    GovernedWriteRequest,
)
from .model import ActionStatus, AuditEntry, ObjectRef, utcnow
from .runtime import CEPIORuntime


class IdentityReconciliationStatus(str, Enum):
    matched = "matched"
    ambiguous = "ambiguous"
    missing = "missing"
    stale = "stale"
    conflict = "conflict"
    verified = "verified"


class ExternalActionStatus(str, Enum):
    pending_execution = "pending_execution"
    dispatching = "dispatching"
    acknowledged = "acknowledged"
    pending_verification = "pending_verification"
    verified = "verified"
    failed = "failed"
    unknown = "unknown"


class ExternalIdentityMapping(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    cepio_object_id: str
    system: str
    identity_type: str = "default"
    external_id: str
    status: IdentityReconciliationStatus = IdentityReconciliationStatus.matched
    mapping_version: str = "1"
    source_timestamp: datetime | None = None
    verified_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


PayloadBuilder = Callable[[AuditEntry], dict[str, Any]]


@dataclass(frozen=True)
class ExternalActionBinding:
    action_type: str
    system: str
    operation: str
    identity_type: str = "default"
    payload_builder: PayloadBuilder | None = None


class ExternalActionExecution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    action_type: str
    target: ObjectRef
    actor_id: str
    actor_roles: set[str] = Field(default_factory=set)
    decision_id: str | None = None
    correlation_id: str | None = None
    workflow_instance_id: str | None = None
    system: str
    operation: str
    identity_type: str = "default"
    external_identity_id: str | None = None
    external_identity_mapping_version: str | None = None
    external_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    status: ExternalActionStatus = ExternalActionStatus.pending_execution
    revision: int = 0
    source_request_id: str | None = None
    source_payload: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None
    failure_reason: str | None = None
    dispatch_attempts: int = 0
    verification_attempts: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    acknowledged_at: datetime | None = None
    verified_at: datetime | None = None


class ExternalActionHistoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    execution_id: str
    event: str
    status: ExternalActionStatus
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utcnow)


class ConcurrentExternalActionUpdate(RuntimeError):
    pass


class ExternalActionRepository(Protocol):
    def save_identity(self, mapping: ExternalIdentityMapping) -> ExternalIdentityMapping: ...
    def list_identities(
        self,
        cepio_object_id: str,
        *,
        system: str | None = None,
        identity_type: str | None = None,
    ) -> list[ExternalIdentityMapping]: ...
    def save_execution(
        self,
        execution: ExternalActionExecution,
        *,
        expected_revision: int | None = None,
    ) -> ExternalActionExecution: ...
    def get_execution(self, execution_id: str) -> ExternalActionExecution | None: ...
    def find_execution_by_idempotency(self, idempotency_key: str) -> ExternalActionExecution | None: ...
    def list_executions(
        self, status: ExternalActionStatus | None = None
    ) -> list[ExternalActionExecution]: ...
    def append_history(self, entry: ExternalActionHistoryEntry) -> ExternalActionHistoryEntry: ...
    def list_history(self, execution_id: str) -> list[ExternalActionHistoryEntry]: ...


class InMemoryExternalActionRepository(ExternalActionRepository):
    def __init__(self) -> None:
        self._identities: dict[str, ExternalIdentityMapping] = {}
        self._executions: dict[str, ExternalActionExecution] = {}
        self._idempotency: dict[str, str] = {}
        self._history: list[ExternalActionHistoryEntry] = []
        self._lock = RLock()

    def save_identity(self, mapping: ExternalIdentityMapping) -> ExternalIdentityMapping:
        with self._lock:
            mapping.updated_at = utcnow()
            self._identities[mapping.id] = mapping.model_copy(deep=True)
            return mapping.model_copy(deep=True)

    def list_identities(
        self,
        cepio_object_id: str,
        *,
        system: str | None = None,
        identity_type: str | None = None,
    ) -> list[ExternalIdentityMapping]:
        with self._lock:
            result = []
            for item in self._identities.values():
                if item.cepio_object_id != cepio_object_id:
                    continue
                if system is not None and item.system != system:
                    continue
                if identity_type is not None and item.identity_type != identity_type:
                    continue
                result.append(item.model_copy(deep=True))
            return sorted(
                result, key=lambda item: (item.system, item.identity_type, item.external_id)
            )

    def save_execution(
        self,
        execution: ExternalActionExecution,
        *,
        expected_revision: int | None = None,
    ) -> ExternalActionExecution:
        with self._lock:
            prior = self._executions.get(execution.id)
            prior_id = self._idempotency.get(execution.idempotency_key)
            if prior_id is not None and prior_id != execution.id:
                raise ValueError(
                    "External action idempotency key already belongs to another execution"
                )
            if prior is None:
                if expected_revision not in (None, 0):
                    raise ConcurrentExternalActionUpdate(
                        f"External action {execution.id} does not exist at revision {expected_revision}"
                    )
                next_revision = 1
            else:
                if (
                    expected_revision is not None
                    and prior.revision != expected_revision
                ):
                    raise ConcurrentExternalActionUpdate(
                        f"External action {execution.id} revision changed from "
                        f"{expected_revision} to {prior.revision}"
                    )
                next_revision = prior.revision + 1
            execution.updated_at = utcnow()
            execution.revision = next_revision
            self._executions[execution.id] = execution.model_copy(deep=True)
            self._idempotency[execution.idempotency_key] = execution.id
            return execution.model_copy(deep=True)

    def get_execution(self, execution_id: str) -> ExternalActionExecution | None:
        with self._lock:
            item = self._executions.get(execution_id)
            return item.model_copy(deep=True) if item else None

    def find_execution_by_idempotency(self, idempotency_key: str) -> ExternalActionExecution | None:
        with self._lock:
            execution_id = self._idempotency.get(idempotency_key)
            item = self._executions.get(execution_id) if execution_id else None
            return item.model_copy(deep=True) if item else None

    def list_executions(
        self, status: ExternalActionStatus | None = None
    ) -> list[ExternalActionExecution]:
        with self._lock:
            values = [item.model_copy(deep=True) for item in self._executions.values()]
            if status is not None:
                values = [item for item in values if item.status == status]
            return sorted(values, key=lambda item: (item.created_at, item.id))

    def append_history(self, entry: ExternalActionHistoryEntry) -> ExternalActionHistoryEntry:
        with self._lock:
            self._history.append(entry)
            return entry

    def list_history(self, execution_id: str) -> list[ExternalActionHistoryEntry]:
        with self._lock:
            return [item for item in self._history if item.execution_id == execution_id]


class SQLiteExternalActionRepository(ExternalActionRepository):
    """Durable reference store with optimistic execution-state concurrency."""

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
                CREATE TABLE IF NOT EXISTS external_identity_mappings (
                    id TEXT PRIMARY KEY,
                    cepio_object_id TEXT NOT NULL,
                    system TEXT NOT NULL,
                    identity_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_external_identity_lookup
                    ON external_identity_mappings(cepio_object_id, system, identity_type, status);

                CREATE TABLE IF NOT EXISTS external_action_executions (
                    id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    system TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_external_action_status
                    ON external_action_executions(status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_external_action_action
                    ON external_action_executions(action_id);

                CREATE TABLE IF NOT EXISTS external_action_history (
                    id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_external_action_history
                    ON external_action_history(execution_id, occurred_at);
                """
            )
            columns = {
                row["name"]
                for row in self._conn.execute(
                    "PRAGMA table_info(external_action_executions)"
                ).fetchall()
            }
            if "revision" not in columns:
                self._conn.execute(
                    "ALTER TABLE external_action_executions ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
                )
            self._conn.commit()

    def save_identity(self, mapping: ExternalIdentityMapping) -> ExternalIdentityMapping:
        with self._lock:
            mapping.updated_at = utcnow()
            self._conn.execute(
                """
                INSERT INTO external_identity_mappings(
                    id, cepio_object_id, system, identity_type, status, payload
                ) VALUES(?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    cepio_object_id=excluded.cepio_object_id,
                    system=excluded.system,
                    identity_type=excluded.identity_type,
                    status=excluded.status,
                    payload=excluded.payload
                """,
                (
                    mapping.id,
                    mapping.cepio_object_id,
                    mapping.system,
                    mapping.identity_type,
                    mapping.status.value,
                    mapping.model_dump_json(),
                ),
            )
            self._conn.commit()
        return mapping.model_copy(deep=True)

    def list_identities(
        self,
        cepio_object_id: str,
        *,
        system: str | None = None,
        identity_type: str | None = None,
    ) -> list[ExternalIdentityMapping]:
        clauses = ["cepio_object_id = ?"]
        params: list[Any] = [cepio_object_id]
        if system is not None:
            clauses.append("system = ?")
            params.append(system)
        if identity_type is not None:
            clauses.append("identity_type = ?")
            params.append(identity_type)
        rows = self._conn.execute(
            f"SELECT payload FROM external_identity_mappings WHERE {' AND '.join(clauses)} "
            "ORDER BY system, identity_type, id",
            tuple(params),
        ).fetchall()
        return [ExternalIdentityMapping.model_validate_json(row["payload"]) for row in rows]

    def save_execution(
        self,
        execution: ExternalActionExecution,
        *,
        expected_revision: int | None = None,
    ) -> ExternalActionExecution:
        with self._lock:
            prior_row = self._conn.execute(
                "SELECT revision, payload FROM external_action_executions WHERE id = ?",
                (execution.id,),
            ).fetchone()
            if prior_row is None:
                if expected_revision not in (None, 0):
                    raise ConcurrentExternalActionUpdate(
                        f"External action {execution.id} does not exist at revision {expected_revision}"
                    )
                execution.revision = 1
                execution.updated_at = utcnow()
                try:
                    self._conn.execute(
                        """
                        INSERT INTO external_action_executions(
                            id, action_id, system, operation, idempotency_key,
                            status, revision, updated_at, payload
                        ) VALUES(?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            execution.id,
                            execution.action_id,
                            execution.system,
                            execution.operation,
                            execution.idempotency_key,
                            execution.status.value,
                            execution.revision,
                            execution.updated_at.isoformat(),
                            execution.model_dump_json(),
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    self._conn.rollback()
                    raise ConcurrentExternalActionUpdate(str(exc)) from exc
                self._conn.commit()
                return execution.model_copy(deep=True)

            prior_revision = int(prior_row["revision"])
            if expected_revision is not None and prior_revision != expected_revision:
                raise ConcurrentExternalActionUpdate(
                    f"External action {execution.id} revision changed from "
                    f"{expected_revision} to {prior_revision}"
                )
            execution.revision = prior_revision + 1
            execution.updated_at = utcnow()
            if expected_revision is None:
                cursor = self._conn.execute(
                    """
                    UPDATE external_action_executions SET
                        action_id=?, system=?, operation=?, idempotency_key=?,
                        status=?, revision=?, updated_at=?, payload=?
                    WHERE id=?
                    """,
                    (
                        execution.action_id,
                        execution.system,
                        execution.operation,
                        execution.idempotency_key,
                        execution.status.value,
                        execution.revision,
                        execution.updated_at.isoformat(),
                        execution.model_dump_json(),
                        execution.id,
                    ),
                )
            else:
                cursor = self._conn.execute(
                    """
                    UPDATE external_action_executions SET
                        action_id=?, system=?, operation=?, idempotency_key=?,
                        status=?, revision=?, updated_at=?, payload=?
                    WHERE id=? AND revision=?
                    """,
                    (
                        execution.action_id,
                        execution.system,
                        execution.operation,
                        execution.idempotency_key,
                        execution.status.value,
                        execution.revision,
                        execution.updated_at.isoformat(),
                        execution.model_dump_json(),
                        execution.id,
                        expected_revision,
                    ),
                )
            if cursor.rowcount != 1:
                self._conn.rollback()
                raise ConcurrentExternalActionUpdate(
                    f"External action {execution.id} was updated concurrently"
                )
            self._conn.commit()
        return execution.model_copy(deep=True)

    def get_execution(self, execution_id: str) -> ExternalActionExecution | None:
        row = self._conn.execute(
            "SELECT payload FROM external_action_executions WHERE id = ?", (execution_id,)
        ).fetchone()
        return ExternalActionExecution.model_validate_json(row["payload"]) if row else None

    def find_execution_by_idempotency(self, idempotency_key: str) -> ExternalActionExecution | None:
        row = self._conn.execute(
            "SELECT payload FROM external_action_executions WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return ExternalActionExecution.model_validate_json(row["payload"]) if row else None

    def list_executions(
        self, status: ExternalActionStatus | None = None
    ) -> list[ExternalActionExecution]:
        if status is None:
            rows = self._conn.execute(
                "SELECT payload FROM external_action_executions ORDER BY updated_at, id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT payload FROM external_action_executions WHERE status = ? ORDER BY updated_at, id",
                (status.value,),
            ).fetchall()
        return [ExternalActionExecution.model_validate_json(row["payload"]) for row in rows]

    def append_history(self, entry: ExternalActionHistoryEntry) -> ExternalActionHistoryEntry:
        with self._lock:
            self._conn.execute(
                "INSERT INTO external_action_history(id, execution_id, occurred_at, payload) VALUES(?,?,?,?)",
                (
                    entry.id,
                    entry.execution_id,
                    entry.occurred_at.isoformat(),
                    entry.model_dump_json(),
                ),
            )
            self._conn.commit()
        return entry

    def list_history(self, execution_id: str) -> list[ExternalActionHistoryEntry]:
        rows = self._conn.execute(
            "SELECT payload FROM external_action_history WHERE execution_id = ? ORDER BY occurred_at, id",
            (execution_id,),
        ).fetchall()
        return [ExternalActionHistoryEntry.model_validate_json(row["payload"]) for row in rows]


class UnsafeExternalRedispatchError(RuntimeError):
    pass


class ExternalActionRuntime:
    """Auditable async control plane for CEPIO-authorized source-system writeback."""

    def __init__(
        self,
        runtime: CEPIORuntime,
        repository: ExternalActionRepository | None = None,
    ) -> None:
        self.runtime = runtime
        self.repository = repository or InMemoryExternalActionRepository()
        self._adapters: dict[str, GovernedWriteAdapter] = {}
        self._bindings: dict[str, ExternalActionBinding] = {}

    def register_adapter(self, adapter: GovernedWriteAdapter) -> None:
        self._adapters[adapter.system_name] = adapter

    def register_binding(self, binding: ExternalActionBinding) -> None:
        if binding.system not in self._adapters:
            raise ValueError(
                f"No governed write adapter registered for system {binding.system}"
            )
        self._bindings[binding.action_type] = binding

    def register_identity(self, mapping: ExternalIdentityMapping) -> ExternalIdentityMapping:
        self.runtime.get_object(mapping.cepio_object_id)
        if (
            mapping.status == IdentityReconciliationStatus.verified
            and mapping.verified_at is None
        ):
            mapping.verified_at = utcnow()
        return self.repository.save_identity(mapping)

    def identities_for(
        self,
        cepio_object_id: str,
        *,
        system: str | None = None,
        identity_type: str | None = None,
    ) -> list[ExternalIdentityMapping]:
        self.runtime.get_object(cepio_object_id)
        return self.repository.list_identities(
            cepio_object_id, system=system, identity_type=identity_type
        )

    def enqueue_from_action(self, action_id: str) -> ExternalActionExecution:
        audit = self._executed_action_audit(action_id)
        binding = self._bindings.get(audit.action_type)
        if binding is None:
            raise KeyError(
                f"No external write binding registered for action type {audit.action_type}"
            )

        idempotency_key = f"external:{binding.system}:{binding.operation}:{audit.action_id}"
        prior = self.repository.find_execution_by_idempotency(idempotency_key)
        if prior is not None:
            return prior

        payload = (
            binding.payload_builder(audit)
            if binding.payload_builder is not None
            else self._default_payload(audit)
        )
        identity, failure_reason = self._resolve_identity(
            audit.target.id,
            system=binding.system,
            identity_type=binding.identity_type,
        )
        execution = ExternalActionExecution(
            action_id=audit.action_id,
            action_type=audit.action_type,
            target=audit.target,
            actor_id=audit.actor_id,
            actor_roles=set(audit.actor_roles),
            decision_id=audit.decision_id,
            correlation_id=audit.correlation_id,
            workflow_instance_id=audit.workflow_instance_id,
            system=binding.system,
            operation=binding.operation,
            identity_type=binding.identity_type,
            external_identity_id=identity.id if identity else None,
            external_identity_mapping_version=(identity.mapping_version if identity else None),
            external_id=identity.external_id if identity else None,
            payload=payload,
            idempotency_key=idempotency_key,
            status=(
                ExternalActionStatus.pending_execution
                if identity is not None
                else ExternalActionStatus.failed
            ),
            failure_reason=failure_reason,
            message=(
                "Governed external write queued"
                if identity is not None
                else f"External write blocked: {failure_reason}"
            ),
        )
        try:
            stored = self.repository.save_execution(execution)
        except ConcurrentExternalActionUpdate:
            prior = self.repository.find_execution_by_idempotency(idempotency_key)
            if prior is None:
                raise
            return prior
        self._history(
            stored,
            "external_write_queued" if identity else "external_write_blocked",
            details={
                "action_id": audit.action_id,
                "system": binding.system,
                "operation": binding.operation,
                "failure_reason": failure_reason,
                "workflow_instance_id": audit.workflow_instance_id,
            },
        )
        return self.get_execution(stored.id)

    def dispatch(self, execution_id: str) -> ExternalActionExecution:
        execution = self.get_execution(execution_id)
        if execution.status in {
            ExternalActionStatus.unknown,
            ExternalActionStatus.dispatching,
        }:
            raise UnsafeExternalRedispatchError(
                "External outcome is in-flight or unknown; reconcile before any redispatch"
            )
        if execution.status in {
            ExternalActionStatus.acknowledged,
            ExternalActionStatus.pending_verification,
            ExternalActionStatus.verified,
            ExternalActionStatus.failed,
        }:
            return execution
        if execution.status != ExternalActionStatus.pending_execution:
            return execution

        identity_reason = self._identity_drift_reason(execution)
        if identity_reason is not None:
            expected = execution.revision
            execution.status = ExternalActionStatus.failed
            execution.failure_reason = identity_reason
            execution.message = "External identity changed after enqueue; write blocked"
            try:
                stored = self.repository.save_execution(
                    execution, expected_revision=expected
                )
            except ConcurrentExternalActionUpdate:
                return self.get_execution(execution.id)
            self._history(
                stored,
                "external_write_blocked_identity_drift",
                details={"reason": identity_reason},
            )
            return stored

        expected = execution.revision
        execution.status = ExternalActionStatus.dispatching
        execution.dispatch_attempts += 1
        try:
            claimed = self.repository.save_execution(
                execution, expected_revision=expected
            )
        except ConcurrentExternalActionUpdate:
            return self.get_execution(execution.id)

        self._history(
            claimed,
            "adapter_dispatch_started",
            details={"attempt": claimed.dispatch_attempts, "revision": claimed.revision},
        )
        adapter = self._adapter(claimed.system)
        try:
            receipt = adapter.write_governed(self._write_request(claimed))
        except Exception as exc:
            claimed.status = ExternalActionStatus.unknown
            claimed.failure_reason = "adapter_write_outcome_unknown"
            claimed.message = str(exc)
            stored = self.repository.save_execution(
                claimed, expected_revision=claimed.revision
            )
            self._history(
                stored,
                "adapter_dispatch_unknown",
                details={"error": str(exc)},
            )
            return stored

        claimed.source_request_id = receipt.source_request_id
        claimed.source_payload = dict(receipt.source_payload)
        claimed.message = receipt.message
        if not receipt.accepted:
            claimed.status = ExternalActionStatus.failed
            claimed.failure_reason = "adapter_rejected_write"
            stored = self.repository.save_execution(
                claimed, expected_revision=claimed.revision
            )
            self._history(
                stored,
                "adapter_dispatch_rejected",
                details={"message": receipt.message},
            )
            return stored

        claimed.status = ExternalActionStatus.acknowledged
        claimed.acknowledged_at = utcnow()
        claimed.failure_reason = None
        acknowledged = self.repository.save_execution(
            claimed, expected_revision=claimed.revision
        )
        self._history(
            acknowledged,
            "adapter_write_acknowledged",
            details={"source_request_id": receipt.source_request_id},
        )

        acknowledged.status = ExternalActionStatus.pending_verification
        pending = self.repository.save_execution(
            acknowledged, expected_revision=acknowledged.revision
        )
        self._history(pending, "external_verification_pending")
        return pending

    def verify(self, execution_id: str) -> ExternalActionExecution:
        execution = self.get_execution(execution_id)
        if execution.status in {
            ExternalActionStatus.unknown,
            ExternalActionStatus.dispatching,
        }:
            raise UnsafeExternalRedispatchError(
                "External outcome is in-flight or unknown; use reconcile() rather than ordinary verification"
            )
        if execution.status in {
            ExternalActionStatus.verified,
            ExternalActionStatus.failed,
        }:
            return execution
        if execution.status not in {
            ExternalActionStatus.acknowledged,
            ExternalActionStatus.pending_verification,
        }:
            raise RuntimeError(
                f"Execution {execution.id} is not ready for verification: {execution.status.value}"
            )
        adapter = self._adapter(execution.system)
        expected = execution.revision
        execution.verification_attempts += 1
        execution = self.repository.save_execution(
            execution, expected_revision=expected
        )
        try:
            result = adapter.verify_write(self._verification_request(execution))
        except Exception as exc:
            return self._mark_unknown(
                execution,
                "verification_error",
                str(exc),
                expected_revision=execution.revision,
            )
        return self._apply_verification(
            execution,
            result,
            event_prefix="verification",
            expected_revision=execution.revision,
        )

    def reconcile(self, execution_id: str) -> ExternalActionExecution:
        execution = self.get_execution(execution_id)
        if execution.status in {
            ExternalActionStatus.verified,
            ExternalActionStatus.failed,
        }:
            return execution
        if execution.status == ExternalActionStatus.pending_execution:
            raise RuntimeError("Cannot reconcile an external action that was never dispatched")
        adapter = self._adapter(execution.system)
        expected = execution.revision
        execution.verification_attempts += 1
        execution = self.repository.save_execution(
            execution, expected_revision=expected
        )
        self._history(execution, "reconciliation_started")
        try:
            result = adapter.reconcile_write(self._verification_request(execution))
        except Exception as exc:
            return self._mark_unknown(
                execution,
                "reconciliation_error",
                str(exc),
                expected_revision=execution.revision,
            )
        return self._apply_verification(
            execution,
            result,
            event_prefix="reconciliation",
            expected_revision=execution.revision,
        )

    def get_execution(self, execution_id: str) -> ExternalActionExecution:
        execution = self.repository.get_execution(execution_id)
        if execution is None:
            raise KeyError(f"Unknown external action execution: {execution_id}")
        return execution

    def list_executions(
        self, status: ExternalActionStatus | None = None
    ) -> list[ExternalActionExecution]:
        return self.repository.list_executions(status)

    def history(self, execution_id: str) -> list[ExternalActionHistoryEntry]:
        self.get_execution(execution_id)
        return self.repository.list_history(execution_id)

    def _executed_action_audit(self, action_id: str) -> AuditEntry:
        audits = self.runtime.audits_for_action(action_id)
        executed = [item for item in audits if item.status == ActionStatus.executed]
        if not executed:
            raise PermissionError(
                "External write requires an immutable audit for a successfully executed CEPIO Action"
            )
        for item in executed:
            if not item.replayed:
                return item
        return executed[0]

    def _resolve_identity(
        self,
        cepio_object_id: str,
        *,
        system: str,
        identity_type: str,
    ) -> tuple[ExternalIdentityMapping | None, str | None]:
        mappings = self.repository.list_identities(
            cepio_object_id,
            system=system,
            identity_type=identity_type,
        )
        if not mappings:
            return None, "identity_missing"
        if any(
            item.status
            in {
                IdentityReconciliationStatus.ambiguous,
                IdentityReconciliationStatus.conflict,
            }
            for item in mappings
        ):
            return None, "identity_conflict_or_ambiguous"
        eligible = [
            item
            for item in mappings
            if item.status
            in {
                IdentityReconciliationStatus.matched,
                IdentityReconciliationStatus.verified,
            }
        ]
        if len(eligible) != 1:
            if not eligible and all(
                item.status == IdentityReconciliationStatus.stale
                for item in mappings
            ):
                return None, "identity_stale"
            return None, "identity_ambiguous"
        if len(mappings) != 1:
            return None, "identity_ambiguous"
        return eligible[0], None

    def _identity_drift_reason(
        self, execution: ExternalActionExecution
    ) -> str | None:
        identity, resolution_error = self._resolve_identity(
            execution.target.id,
            system=execution.system,
            identity_type=execution.identity_type,
        )
        if identity is None:
            return f"identity_changed_before_dispatch:{resolution_error}"
        if identity.id != execution.external_identity_id:
            return "identity_changed_before_dispatch:mapping_changed"
        if identity.external_id != execution.external_id:
            return "identity_changed_before_dispatch:external_id_changed"
        if identity.mapping_version != execution.external_identity_mapping_version:
            return "identity_changed_before_dispatch:mapping_version_changed"
        return None

    def _adapter(self, system: str) -> GovernedWriteAdapter:
        adapter = self._adapters.get(system)
        if adapter is None:
            raise KeyError(f"No governed write adapter registered for system {system}")
        return adapter

    @staticmethod
    def _default_payload(audit: AuditEntry) -> dict[str, Any]:
        return {
            "action_type": audit.action_type,
            "canonical_target": {"id": audit.target.id, "type": audit.target.type},
            "decision_id": audit.decision_id,
            "effects": dict(audit.effects),
        }

    @staticmethod
    def _write_request(execution: ExternalActionExecution) -> GovernedWriteRequest:
        if execution.external_id is None:
            raise RuntimeError("External identity is required before write dispatch")
        return GovernedWriteRequest(
            execution_id=execution.id,
            system=execution.system,
            operation=execution.operation,
            external_id=execution.external_id,
            canonical_object_id=execution.target.id,
            action_id=execution.action_id,
            actor_id=execution.actor_id,
            decision_id=execution.decision_id,
            idempotency_key=execution.idempotency_key,
            payload=dict(execution.payload),
        )

    @staticmethod
    def _verification_request(
        execution: ExternalActionExecution,
    ) -> GovernedVerificationRequest:
        if execution.external_id is None:
            raise RuntimeError("External identity is required before verification")
        return GovernedVerificationRequest(
            execution_id=execution.id,
            system=execution.system,
            operation=execution.operation,
            external_id=execution.external_id,
            canonical_object_id=execution.target.id,
            action_id=execution.action_id,
            idempotency_key=execution.idempotency_key,
            source_request_id=execution.source_request_id,
            expected_payload=dict(execution.payload),
        )

    def _apply_verification(
        self,
        execution: ExternalActionExecution,
        result: GovernedVerificationResult,
        *,
        event_prefix: str,
        expected_revision: int,
    ) -> ExternalActionExecution:
        execution.source_payload = dict(result.source_payload)
        execution.message = result.message
        if result.status == AdapterVerificationStatus.verified:
            execution.status = ExternalActionStatus.verified
            execution.verified_at = utcnow()
            execution.failure_reason = None
        elif result.status == AdapterVerificationStatus.not_applied:
            execution.status = ExternalActionStatus.failed
            execution.failure_reason = "source_confirms_not_applied"
        else:
            execution.status = ExternalActionStatus.unknown
            execution.failure_reason = (
                "source_conflict"
                if result.status == AdapterVerificationStatus.conflict
                else "source_outcome_unknown"
            )
        stored = self.repository.save_execution(
            execution, expected_revision=expected_revision
        )
        self._history(
            stored,
            f"{event_prefix}_{stored.status.value}",
            details={
                "adapter_status": result.status.value,
                "message": result.message,
            },
        )
        return stored

    def _mark_unknown(
        self,
        execution: ExternalActionExecution,
        reason: str,
        message: str,
        *,
        expected_revision: int,
    ) -> ExternalActionExecution:
        execution.status = ExternalActionStatus.unknown
        execution.failure_reason = reason
        execution.message = message
        stored = self.repository.save_execution(
            execution, expected_revision=expected_revision
        )
        self._history(
            stored,
            "external_outcome_unknown",
            details={"reason": reason, "message": message},
        )
        return stored

    def _history(
        self,
        execution: ExternalActionExecution,
        event: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.repository.append_history(
            ExternalActionHistoryEntry(
                execution_id=execution.id,
                event=event,
                status=execution.status,
                details=details or {},
            )
        )


def build_external_action_runtime(
    runtime: CEPIORuntime,
    *,
    sqlite_path: str | Path | None = None,
) -> ExternalActionRuntime:
    repository: ExternalActionRepository
    if sqlite_path is None:
        repository = InMemoryExternalActionRepository()
    else:
        repository = SQLiteExternalActionRepository(sqlite_path)
    return ExternalActionRuntime(runtime, repository)