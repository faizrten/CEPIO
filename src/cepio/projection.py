from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from .model import OntologyObject, OperationalEvent, utcnow
from .repositories import EventRepository, ObjectRepository


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_name(value: str) -> str:
    return value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def deterministic_events(events: list[OperationalEvent]) -> list[OperationalEvent]:
    return sorted(events, key=lambda event: (_as_utc(event.occurred_at), event.id))


def _state_hash(state: dict[str, Any]) -> str:
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ProjectionCheckpoint(BaseModel):
    projector: str
    projector_version: str
    subject_id: str
    state: dict[str, Any] = Field(default_factory=dict)
    event_count: int
    last_event_id: str | None = None
    last_event_at: datetime | None = None
    state_hash: str
    rebuilt_at: datetime = Field(default_factory=utcnow)


class ProjectionRepository(Protocol):
    def save_checkpoint(self, checkpoint: ProjectionCheckpoint) -> ProjectionCheckpoint: ...
    def get_checkpoint(self, projector: str, subject_id: str) -> ProjectionCheckpoint | None: ...
    def delete_checkpoint(self, projector: str, subject_id: str) -> None: ...


class InMemoryProjectionRepository(ProjectionRepository):
    def __init__(self) -> None:
        self._checkpoints: dict[tuple[str, str], ProjectionCheckpoint] = {}

    def save_checkpoint(self, checkpoint: ProjectionCheckpoint) -> ProjectionCheckpoint:
        key = (checkpoint.projector, checkpoint.subject_id)
        self._checkpoints[key] = checkpoint.model_copy(deep=True)
        return checkpoint.model_copy(deep=True)

    def get_checkpoint(self, projector: str, subject_id: str) -> ProjectionCheckpoint | None:
        value = self._checkpoints.get((projector, subject_id))
        return value.model_copy(deep=True) if value else None

    def delete_checkpoint(self, projector: str, subject_id: str) -> None:
        self._checkpoints.pop((projector, subject_id), None)


class SQLiteProjectionRepository(ProjectionRepository):
    """Projection metadata store kept separate from immutable source events."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projection_checkpoints (
                projector TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                projector_version TEXT NOT NULL,
                rebuilt_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY(projector, subject_id)
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def save_checkpoint(self, checkpoint: ProjectionCheckpoint) -> ProjectionCheckpoint:
        self._conn.execute(
            """
            INSERT INTO projection_checkpoints(projector,subject_id,projector_version,rebuilt_at,payload)
            VALUES(?,?,?,?,?)
            ON CONFLICT(projector,subject_id) DO UPDATE SET
                projector_version=excluded.projector_version,
                rebuilt_at=excluded.rebuilt_at,
                payload=excluded.payload
            """,
            (
                checkpoint.projector,
                checkpoint.subject_id,
                checkpoint.projector_version,
                checkpoint.rebuilt_at.isoformat(),
                checkpoint.model_dump_json(),
            ),
        )
        self._conn.commit()
        return checkpoint.model_copy(deep=True)

    def get_checkpoint(self, projector: str, subject_id: str) -> ProjectionCheckpoint | None:
        row = self._conn.execute(
            "SELECT payload FROM projection_checkpoints WHERE projector=? AND subject_id=?",
            (projector, subject_id),
        ).fetchone()
        return ProjectionCheckpoint.model_validate_json(row["payload"]) if row else None

    def delete_checkpoint(self, projector: str, subject_id: str) -> None:
        self._conn.execute(
            "DELETE FROM projection_checkpoints WHERE projector=? AND subject_id=?",
            (projector, subject_id),
        )
        self._conn.commit()


class StateProjector(Protocol):
    name: str
    version: str
    state_properties: frozenset[str]

    def initial_state(self, subject: OntologyObject) -> dict[str, Any]: ...
    def apply(self, state: dict[str, Any], event: OperationalEvent) -> dict[str, Any]: ...


class CompressorOperatingStateProjector:
    """Reference projector for rotating-equipment operating state.

    Source events are never changed. The projector is intentionally deterministic:
    only event type/properties plus stable `(occurred_at, id)` ordering influence the
    resulting state.
    """

    name = "compressor-operating-state"
    version = "1.0.0"
    state_properties = frozenset({"operatingState", "lastStateEventId", "lastStateChangedAt"})

    EVENT_STATE = {
        "TripEvent": "tripped",
        "CompressorTrip": "tripped",
        "RecoveryEvent": "running",
        "CompressorRecovery": "running",
        "StartEvent": "running",
        "StartedEvent": "running",
        "StopEvent": "stopped",
        "StoppedEvent": "stopped",
        "DegradationEvent": "degraded",
        "ConditionAlert": "degraded",
        "MaintenanceStartedEvent": "maintenance",
        "MaintenanceCompletedEvent": "stopped",
    }

    def initial_state(self, subject: OntologyObject) -> dict[str, Any]:
        return {
            "operatingState": "unknown",
            "lastStateEventId": None,
            "lastStateChangedAt": None,
        }

    def apply(self, state: dict[str, Any], event: OperationalEvent) -> dict[str, Any]:
        updated = dict(state)
        explicit = event.properties.get("operatingState")
        event_state = explicit if explicit is not None else self.EVENT_STATE.get(_local_name(event.type))
        if event_state is None:
            return updated
        updated["operatingState"] = str(event_state)
        updated["lastStateEventId"] = event.id
        updated["lastStateChangedAt"] = _as_utc(event.occurred_at).isoformat()
        return updated


class ProjectionEngine:
    def __init__(
        self,
        object_repository: ObjectRepository,
        event_repository: EventRepository,
        checkpoint_repository: ProjectionRepository,
    ) -> None:
        self.object_repository = object_repository
        self.event_repository = event_repository
        self.checkpoint_repository = checkpoint_repository

    def rebuild(self, subject_id: str, projector: StateProjector) -> ProjectionCheckpoint:
        subject = self.object_repository.get_object(subject_id)
        if subject is None:
            raise KeyError(f"Unknown CEPIO object: {subject_id}")

        events = deterministic_events(self.event_repository.events_for(subject_id))
        state = projector.initial_state(subject)
        for event in events:
            state = projector.apply(state, event)

        new_properties = dict(subject.properties)
        for key in projector.state_properties:
            if key in state:
                new_properties[key] = state[key]
            else:
                new_properties.pop(key, None)

        if new_properties != subject.properties:
            updated = subject.model_copy(update={"properties": new_properties})
            self.object_repository.upsert_object(updated, expected_version=subject.version)

        last_event = events[-1] if events else None
        checkpoint = ProjectionCheckpoint(
            projector=projector.name,
            projector_version=projector.version,
            subject_id=subject_id,
            state=state,
            event_count=len(events),
            last_event_id=last_event.id if last_event else None,
            last_event_at=_as_utc(last_event.occurred_at) if last_event else None,
            state_hash=_state_hash(state),
        )
        return self.checkpoint_repository.save_checkpoint(checkpoint)

    def clear_projection(self, subject_id: str, projector: StateProjector) -> OntologyObject:
        subject = self.object_repository.get_object(subject_id)
        if subject is None:
            raise KeyError(f"Unknown CEPIO object: {subject_id}")
        properties = dict(subject.properties)
        for key in projector.state_properties:
            properties.pop(key, None)
        if properties != subject.properties:
            subject = self.object_repository.upsert_object(
                subject.model_copy(update={"properties": properties}),
                expected_version=subject.version,
            )
        self.checkpoint_repository.delete_checkpoint(projector.name, subject_id)
        return subject

    def rebuild_from_empty_projection(self, subject_id: str, projector: StateProjector) -> ProjectionCheckpoint:
        self.clear_projection(subject_id, projector)
        return self.rebuild(subject_id, projector)
