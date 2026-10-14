from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Protocol

from .model import ActionResult, AuditEntry, Decision, OntologyObject, OperationalEvent, Relationship, utcnow


class ConcurrencyError(RuntimeError):
    pass


class DuplicateRelationshipError(RuntimeError):
    pass


class ObjectRepository(Protocol):
    def get_object(self, object_id: str) -> OntologyObject | None: ...
    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject: ...
    def list_objects(self, object_type: str | None = None) -> list[OntologyObject]: ...
    def add_relationship(self, rel: Relationship) -> Relationship: ...
    def get_relationships(self, object_id: str, direction: str = "out") -> list[Relationship]: ...


class EventRepository(Protocol):
    def append_event(self, event: OperationalEvent) -> OperationalEvent: ...
    def events_for(self, object_id: str) -> list[OperationalEvent]: ...


class AuditRepository(Protocol):
    def append_audit(self, entry: AuditEntry) -> AuditEntry: ...
    def audits_for_action(self, action_id: str) -> list[AuditEntry]: ...
    def all_audits(self) -> list[AuditEntry]: ...
    def get_idempotent_result(self, key: str) -> ActionResult | None: ...
    def store_idempotent_result(self, key: str, result: ActionResult) -> None: ...


class DecisionRepository(Protocol):
    def save_decision(self, decision: Decision) -> Decision: ...
    def get_decision(self, decision_id: str) -> Decision | None: ...
    def list_decisions(self) -> list[Decision]: ...


class InMemoryRepository(ObjectRepository, EventRepository, AuditRepository, DecisionRepository):
    def __init__(self) -> None:
        self._objects: dict[str, OntologyObject] = {}
        self._relationships: dict[str, Relationship] = {}
        self._outgoing: dict[str, list[str]] = defaultdict(list)
        self._incoming: dict[str, list[str]] = defaultdict(list)
        self._events: list[OperationalEvent] = []
        self._audits: list[AuditEntry] = []
        self._idempotent_results: dict[str, ActionResult] = {}
        self._decisions: dict[str, Decision] = {}
        self._lock = RLock()

    def get_object(self, object_id: str) -> OntologyObject | None:
        obj = self._objects.get(object_id)
        return obj.model_copy(deep=True) if obj else None

    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject:
        with self._lock:
            prior = self._objects.get(obj.id)
            now = utcnow()
            if prior is None:
                if expected_version not in (None, 0):
                    raise ConcurrencyError(f"Object {obj.id} does not exist; expected version {expected_version} cannot match")
                stored = obj.model_copy(deep=True)
                stored.version = 1
                stored.created_at = obj.created_at
                stored.updated_at = now
            else:
                if expected_version is not None and prior.version != expected_version:
                    raise ConcurrencyError(f"Object {obj.id} version mismatch: expected {expected_version}, actual {prior.version}")
                stored = obj.model_copy(deep=True)
                stored.version = prior.version + 1
                stored.created_at = prior.created_at
                stored.updated_at = now
            self._objects[obj.id] = stored
            return stored.model_copy(deep=True)

    def list_objects(self, object_type: str | None = None) -> list[OntologyObject]:
        values = self._objects.values()
        if object_type:
            values = [o for o in values if o.type == object_type]
        return [o.model_copy(deep=True) for o in values]

    def add_relationship(self, rel: Relationship) -> Relationship:
        with self._lock:
            if rel.id in self._relationships:
                raise DuplicateRelationshipError(f"Relationship already exists: {rel.id}")
            stored = rel.model_copy(deep=True)
            self._relationships[rel.id] = stored
            self._outgoing[rel.source.id].append(rel.id)
            self._incoming[rel.target.id].append(rel.id)
            return stored.model_copy(deep=True)

    def get_relationships(self, object_id: str, direction: str = "out") -> list[Relationship]:
        if direction not in {"out", "in"}:
            raise ValueError("direction must be 'out' or 'in'")
        ids = self._outgoing[object_id] if direction == "out" else self._incoming[object_id]
        return [self._relationships[i].model_copy(deep=True) for i in ids]

    def append_event(self, event: OperationalEvent) -> OperationalEvent:
        stored = event.model_copy(deep=True)
        self._events.append(stored)
        return stored.model_copy(deep=True)

    def events_for(self, object_id: str) -> list[OperationalEvent]:
        return [e.model_copy(deep=True) for e in self._events if e.subject.id == object_id]

    def append_audit(self, entry: AuditEntry) -> AuditEntry:
        self._audits.append(entry)
        return entry

    def audits_for_action(self, action_id: str) -> list[AuditEntry]:
        return [a for a in self._audits if a.action_id == action_id]

    def all_audits(self) -> list[AuditEntry]:
        return list(self._audits)

    def get_idempotent_result(self, key: str) -> ActionResult | None:
        result = self._idempotent_results.get(key)
        return result.model_copy(deep=True) if result else None

    def store_idempotent_result(self, key: str, result: ActionResult) -> None:
        if key not in self._idempotent_results:
            self._idempotent_results[key] = result.model_copy(deep=True)

    def save_decision(self, decision: Decision) -> Decision:
        prior = self._decisions.get(decision.id)
        stored = decision.model_copy(deep=True)
        if prior:
            stored.created_at = prior.created_at
            stored.updated_at = utcnow()
        self._decisions[decision.id] = stored
        return stored.model_copy(deep=True)

    def get_decision(self, decision_id: str) -> Decision | None:
        decision = self._decisions.get(decision_id)
        return decision.model_copy(deep=True) if decision else None

    def list_decisions(self) -> list[Decision]:
        return [d.model_copy(deep=True) for d in self._decisions.values()]


class SQLiteRepository(ObjectRepository, EventRepository, AuditRepository, DecisionRepository):
    """Reference SQLite persistence backend."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = RLock()
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS objects (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(type);
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES objects(id),
                FOREIGN KEY(target_id) REFERENCES objects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
            CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
            CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(type);
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY(subject_id) REFERENCES objects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_event_subject ON events(subject_id);
            CREATE TABLE IF NOT EXISTS audits (
                id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                status TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audits(action_id);
            CREATE TABLE IF NOT EXISTS idempotency (
                idempotency_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    @staticmethod
    def _dump(model: object) -> str:
        if hasattr(model, "model_dump_json"):
            return model.model_dump_json()
        return json.dumps(model)

    def get_object(self, object_id: str) -> OntologyObject | None:
        row = self._conn.execute("SELECT payload FROM objects WHERE id = ?", (object_id,)).fetchone()
        return OntologyObject.model_validate_json(row["payload"]) if row else None

    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute("SELECT payload, version, created_at FROM objects WHERE id = ?", (obj.id,)).fetchone()
                now = utcnow()
                if row is None:
                    if expected_version not in (None, 0):
                        raise ConcurrencyError(f"Object {obj.id} does not exist; expected version {expected_version} cannot match")
                    stored = obj.model_copy(deep=True)
                    stored.version = 1
                    stored.updated_at = now
                    self._conn.execute("INSERT INTO objects(id,type,name,payload,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (stored.id, stored.type, stored.name, self._dump(stored), stored.version, stored.created_at.isoformat(), stored.updated_at.isoformat()))
                else:
                    current_version = int(row["version"])
                    if expected_version is not None and current_version != expected_version:
                        raise ConcurrencyError(f"Object {obj.id} version mismatch: expected {expected_version}, actual {current_version}")
                    prior = OntologyObject.model_validate_json(row["payload"])
                    stored = obj.model_copy(deep=True)
                    stored.version = current_version + 1
                    stored.created_at = prior.created_at
                    stored.updated_at = now
                    self._conn.execute("UPDATE objects SET type=?,name=?,payload=?,version=?,updated_at=? WHERE id=?", (stored.type, stored.name, self._dump(stored), stored.version, stored.updated_at.isoformat(), stored.id))
                self._conn.commit()
                return stored
            except Exception:
                self._conn.rollback()
                raise

    def list_objects(self, object_type: str | None = None) -> list[OntologyObject]:
        if object_type:
            rows = self._conn.execute("SELECT payload FROM objects WHERE type = ? ORDER BY id", (object_type,)).fetchall()
        else:
            rows = self._conn.execute("SELECT payload FROM objects ORDER BY id").fetchall()
        return [OntologyObject.model_validate_json(r["payload"]) for r in rows]

    def add_relationship(self, rel: Relationship) -> Relationship:
        try:
            self._conn.execute("INSERT INTO relationships(id,type,source_id,target_id,payload) VALUES(?,?,?,?,?)", (rel.id, rel.type, rel.source.id, rel.target.id, self._dump(rel)))
            self._conn.commit()
            return rel
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: relationships.id" in str(exc):
                raise DuplicateRelationshipError(f"Relationship already exists: {rel.id}") from exc
            raise

    def get_relationships(self, object_id: str, direction: str = "out") -> list[Relationship]:
        if direction == "out":
            rows = self._conn.execute("SELECT payload FROM relationships WHERE source_id = ? ORDER BY id", (object_id,)).fetchall()
        elif direction == "in":
            rows = self._conn.execute("SELECT payload FROM relationships WHERE target_id = ? ORDER BY id", (object_id,)).fetchall()
        else:
            raise ValueError("direction must be 'out' or 'in'")
        return [Relationship.model_validate_json(r["payload"]) for r in rows]

    def append_event(self, event: OperationalEvent) -> OperationalEvent:
        self._conn.execute("INSERT INTO events(id,subject_id,type,occurred_at,payload) VALUES(?,?,?,?,?)", (event.id, event.subject.id, event.type, event.occurred_at.isoformat(), self._dump(event)))
        self._conn.commit()
        return event

    def events_for(self, object_id: str) -> list[OperationalEvent]:
        rows = self._conn.execute("SELECT payload FROM events WHERE subject_id = ? ORDER BY occurred_at", (object_id,)).fetchall()
        return [OperationalEvent.model_validate_json(r["payload"]) for r in rows]

    def append_audit(self, entry: AuditEntry) -> AuditEntry:
        self._conn.execute("INSERT INTO audits(id,action_id,action_type,actor_id,target_id,status,occurred_at,payload) VALUES(?,?,?,?,?,?,?,?)", (entry.id, entry.action_id, entry.action_type, entry.actor_id, entry.target.id, entry.status.value, entry.occurred_at.isoformat(), self._dump(entry)))
        self._conn.commit()
        return entry

    def audits_for_action(self, action_id: str) -> list[AuditEntry]:
        rows = self._conn.execute("SELECT payload FROM audits WHERE action_id = ? ORDER BY occurred_at", (action_id,)).fetchall()
        return [AuditEntry.model_validate_json(r["payload"]) for r in rows]

    def all_audits(self) -> list[AuditEntry]:
        rows = self._conn.execute("SELECT payload FROM audits ORDER BY occurred_at").fetchall()
        return [AuditEntry.model_validate_json(r["payload"]) for r in rows]

    def get_idempotent_result(self, key: str) -> ActionResult | None:
        row = self._conn.execute("SELECT payload FROM idempotency WHERE idempotency_key = ?", (key,)).fetchone()
        return ActionResult.model_validate_json(row["payload"]) if row else None

    def store_idempotent_result(self, key: str, result: ActionResult) -> None:
        self._conn.execute("INSERT OR IGNORE INTO idempotency(idempotency_key,payload,created_at) VALUES(?,?,?)", (key, self._dump(result), utcnow().isoformat()))
        self._conn.commit()

    def save_decision(self, decision: Decision) -> Decision:
        existing = self.get_decision(decision.id)
        stored = decision.model_copy(deep=True)
        if existing:
            stored.created_at = existing.created_at
            stored.updated_at = utcnow()
            self._conn.execute("UPDATE decisions SET subject_id=?, updated_at=?, payload=? WHERE id=?", (stored.subject.id, stored.updated_at.isoformat(), self._dump(stored), stored.id))
        else:
            self._conn.execute("INSERT INTO decisions(id,subject_id,created_at,updated_at,payload) VALUES(?,?,?,?,?)", (stored.id, stored.subject.id, stored.created_at.isoformat(), stored.updated_at.isoformat(), self._dump(stored)))
        self._conn.commit()
        return stored

    def get_decision(self, decision_id: str) -> Decision | None:
        row = self._conn.execute("SELECT payload FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return Decision.model_validate_json(row["payload"]) if row else None

    def list_decisions(self) -> list[Decision]:
        rows = self._conn.execute("SELECT payload FROM decisions ORDER BY created_at").fetchall()
        return [Decision.model_validate_json(r["payload"]) for r in rows]
