from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Protocol

from pydantic import BaseModel

from .model import OntologyObject, Relationship, utcnow
from .repositories import InMemoryRepository, SQLiteRepository

CORE_VALID_FROM = "https://cepio.org/ontology/core#validFrom"
CORE_VALID_TO = "https://cepio.org/ontology/core#validTo"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_dt(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _as_utc(parsed)
    raise ValueError(f"Expected datetime-compatible value, got {type(value).__name__}")


def _object_valid_interval(obj: OntologyObject, transaction_time: datetime) -> tuple[datetime, datetime | None]:
    props = obj.properties
    valid_from = _parse_dt(props.get(CORE_VALID_FROM) or props.get("cepio:validFrom") or props.get("validFrom"))
    valid_to = _parse_dt(props.get(CORE_VALID_TO) or props.get("cepio:validTo") or props.get("validTo"))
    return valid_from or transaction_time, valid_to


def _contains(instant: datetime, valid_from: datetime | None, valid_to: datetime | None) -> bool:
    instant = _as_utc(instant)
    if valid_from is not None and instant < _as_utc(valid_from):
        return False
    if valid_to is not None and instant >= _as_utc(valid_to):
        return False
    return True


class ObjectVersionSnapshot(BaseModel):
    object: OntologyObject
    transaction_time: datetime
    valid_from: datetime
    valid_to: datetime | None = None


class RelationshipVersionSnapshot(BaseModel):
    relationship: Relationship
    revision: int
    transaction_time: datetime


class TemporalRepository(Protocol):
    def get_object_at(self, object_id: str, transaction_time: datetime) -> OntologyObject | None: ...
    def get_object_valid_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        as_of_transaction: datetime | None = None,
    ) -> OntologyObject | None: ...
    def object_history(self, object_id: str) -> list[ObjectVersionSnapshot]: ...
    def relationships_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        direction: str = "out",
        as_of_transaction: datetime | None = None,
    ) -> list[Relationship]: ...
    def relationship_history(self, relationship_id: str) -> list[RelationshipVersionSnapshot]: ...
    def revise_relationship_validity(
        self,
        relationship_id: str,
        *,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Relationship: ...


class TemporalInMemoryRepository(InMemoryRepository, TemporalRepository):
    """In-memory repository with immutable transaction history and valid-time queries.

    `transaction_time` answers when CEPIO recorded a fact. `valid_from`/`valid_to`
    answer when that fact is considered true in the operational domain. Object valid
    time defaults to transaction time unless canonical `validFrom`/`validTo`
    properties explicitly supply source-domain valid time.
    """

    def __init__(self) -> None:
        super().__init__()
        self._object_versions: dict[str, list[ObjectVersionSnapshot]] = defaultdict(list)
        self._relationship_versions: dict[str, list[RelationshipVersionSnapshot]] = defaultdict(list)
        self._temporal_lock = RLock()

    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject:
        with self._temporal_lock:
            stored = super().upsert_object(obj, expected_version=expected_version)
            tx = _as_utc(stored.updated_at)
            valid_from, valid_to = _object_valid_interval(stored, tx)
            self._object_versions[stored.id].append(
                ObjectVersionSnapshot(
                    object=stored.model_copy(deep=True),
                    transaction_time=tx,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
            )
            return stored

    def get_object_at(self, object_id: str, transaction_time: datetime) -> OntologyObject | None:
        target = _as_utc(transaction_time)
        eligible = [s for s in self._object_versions.get(object_id, []) if _as_utc(s.transaction_time) <= target]
        if not eligible:
            return None
        return max(eligible, key=lambda s: (s.transaction_time, s.object.version)).object.model_copy(deep=True)

    def get_object_valid_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        as_of_transaction: datetime | None = None,
    ) -> OntologyObject | None:
        snapshots = self._object_versions.get(object_id, [])
        if as_of_transaction is not None:
            tx = _as_utc(as_of_transaction)
            snapshots = [s for s in snapshots if _as_utc(s.transaction_time) <= tx]
        candidates = [s for s in snapshots if _contains(valid_time, s.valid_from, s.valid_to)]
        if not candidates:
            return None
        return max(candidates, key=lambda s: (s.transaction_time, s.object.version)).object.model_copy(deep=True)

    def object_history(self, object_id: str) -> list[ObjectVersionSnapshot]:
        return [s.model_copy(deep=True) for s in self._object_versions.get(object_id, [])]

    def add_relationship(self, rel: Relationship) -> Relationship:
        with self._temporal_lock:
            stored = super().add_relationship(rel)
            self._relationship_versions[stored.id].append(
                RelationshipVersionSnapshot(
                    relationship=stored.model_copy(deep=True),
                    revision=1,
                    transaction_time=utcnow(),
                )
            )
            return stored

    def relationship_history(self, relationship_id: str) -> list[RelationshipVersionSnapshot]:
        return [s.model_copy(deep=True) for s in self._relationship_versions.get(relationship_id, [])]

    def revise_relationship_validity(
        self,
        relationship_id: str,
        *,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Relationship:
        with self._temporal_lock:
            current = self._relationships.get(relationship_id)
            if current is None:
                raise KeyError(f"Unknown relationship: {relationship_id}")
            revised = current.model_copy(deep=True)
            if valid_from is not None:
                revised.valid_from = valid_from
            if valid_to is not None:
                revised.valid_to = valid_to
            self._relationships[relationship_id] = revised.model_copy(deep=True)
            revision = len(self._relationship_versions[relationship_id]) + 1
            self._relationship_versions[relationship_id].append(
                RelationshipVersionSnapshot(
                    relationship=revised.model_copy(deep=True),
                    revision=revision,
                    transaction_time=utcnow(),
                )
            )
            return revised

    def relationships_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        direction: str = "out",
        as_of_transaction: datetime | None = None,
    ) -> list[Relationship]:
        if direction not in {"out", "in"}:
            raise ValueError("direction must be 'out' or 'in'")
        result: list[Relationship] = []
        tx_limit = _as_utc(as_of_transaction) if as_of_transaction else None
        for snapshots in self._relationship_versions.values():
            eligible = snapshots
            if tx_limit is not None:
                eligible = [s for s in snapshots if _as_utc(s.transaction_time) <= tx_limit]
            if not eligible:
                continue
            chosen = max(eligible, key=lambda s: (s.transaction_time, s.revision)).relationship
            endpoint = chosen.source.id if direction == "out" else chosen.target.id
            if endpoint != object_id:
                continue
            if _contains(valid_time, chosen.valid_from, chosen.valid_to):
                result.append(chosen.model_copy(deep=True))
        return sorted(result, key=lambda r: r.id)

    def events_for(self, object_id: str):
        events = super().events_for(object_id)
        return sorted(events, key=lambda e: (_as_utc(e.occurred_at), e.id))


class TemporalSQLiteRepository(SQLiteRepository, TemporalRepository):
    """SQLite reference backend for CEPIO bitemporal history."""

    def _init_schema(self) -> None:
        super()._init_schema()
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS object_history (
                object_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                transaction_time TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY(object_id, version)
            );
            CREATE INDEX IF NOT EXISTS idx_object_history_tx ON object_history(object_id, transaction_time);
            CREATE INDEX IF NOT EXISTS idx_object_history_valid ON object_history(object_id, valid_from, valid_to);

            CREATE TABLE IF NOT EXISTS relationship_history (
                relationship_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                transaction_time TEXT NOT NULL,
                valid_from TEXT,
                valid_to TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY(relationship_id, revision)
            );
            CREATE INDEX IF NOT EXISTS idx_relationship_history_tx ON relationship_history(relationship_id, transaction_time);
            """
        )
        self._conn.commit()

    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject:
        with self._lock:
            stored = super().upsert_object(obj, expected_version=expected_version)
            tx = _as_utc(stored.updated_at)
            valid_from, valid_to = _object_valid_interval(stored, tx)
            self._conn.execute(
                "INSERT INTO object_history(object_id,version,transaction_time,valid_from,valid_to,payload) VALUES(?,?,?,?,?,?)",
                (
                    stored.id,
                    stored.version,
                    tx.isoformat(),
                    valid_from.isoformat(),
                    valid_to.isoformat() if valid_to else None,
                    self._dump(stored),
                ),
            )
            self._conn.commit()
            return stored

    def get_object_at(self, object_id: str, transaction_time: datetime) -> OntologyObject | None:
        row = self._conn.execute(
            "SELECT payload FROM object_history WHERE object_id=? AND transaction_time<=? ORDER BY transaction_time DESC, version DESC LIMIT 1",
            (object_id, _as_utc(transaction_time).isoformat()),
        ).fetchone()
        return OntologyObject.model_validate_json(row["payload"]) if row else None

    def get_object_valid_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        as_of_transaction: datetime | None = None,
    ) -> OntologyObject | None:
        valid = _as_utc(valid_time).isoformat()
        sql = "SELECT payload FROM object_history WHERE object_id=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?)"
        params: list[object] = [object_id, valid, valid]
        if as_of_transaction is not None:
            sql += " AND transaction_time<=?"
            params.append(_as_utc(as_of_transaction).isoformat())
        sql += " ORDER BY transaction_time DESC, version DESC LIMIT 1"
        row = self._conn.execute(sql, tuple(params)).fetchone()
        return OntologyObject.model_validate_json(row["payload"]) if row else None

    def object_history(self, object_id: str) -> list[ObjectVersionSnapshot]:
        rows = self._conn.execute(
            "SELECT payload,transaction_time,valid_from,valid_to FROM object_history WHERE object_id=? ORDER BY version",
            (object_id,),
        ).fetchall()
        return [
            ObjectVersionSnapshot(
                object=OntologyObject.model_validate_json(row["payload"]),
                transaction_time=datetime.fromisoformat(row["transaction_time"]),
                valid_from=datetime.fromisoformat(row["valid_from"]),
                valid_to=datetime.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
            )
            for row in rows
        ]

    def add_relationship(self, rel: Relationship) -> Relationship:
        with self._lock:
            stored = super().add_relationship(rel)
            self._conn.execute(
                "INSERT INTO relationship_history(relationship_id,revision,transaction_time,valid_from,valid_to,payload) VALUES(?,?,?,?,?,?)",
                (
                    stored.id,
                    1,
                    utcnow().isoformat(),
                    stored.valid_from.isoformat() if stored.valid_from else None,
                    stored.valid_to.isoformat() if stored.valid_to else None,
                    self._dump(stored),
                ),
            )
            self._conn.commit()
            return stored

    def relationship_history(self, relationship_id: str) -> list[RelationshipVersionSnapshot]:
        rows = self._conn.execute(
            "SELECT revision,transaction_time,payload FROM relationship_history WHERE relationship_id=? ORDER BY revision",
            (relationship_id,),
        ).fetchall()
        return [
            RelationshipVersionSnapshot(
                relationship=Relationship.model_validate_json(row["payload"]),
                revision=int(row["revision"]),
                transaction_time=datetime.fromisoformat(row["transaction_time"]),
            )
            for row in rows
        ]

    def revise_relationship_validity(
        self,
        relationship_id: str,
        *,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Relationship:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM relationships WHERE id=?", (relationship_id,)
            ).fetchone()
            if not row:
                raise KeyError(f"Unknown relationship: {relationship_id}")
            revised = Relationship.model_validate_json(row["payload"])
            if valid_from is not None:
                revised.valid_from = valid_from
            if valid_to is not None:
                revised.valid_to = valid_to
            revision_row = self._conn.execute(
                "SELECT COALESCE(MAX(revision),0) AS revision FROM relationship_history WHERE relationship_id=?",
                (relationship_id,),
            ).fetchone()
            revision = int(revision_row["revision"]) + 1
            tx = utcnow()
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute(
                    "UPDATE relationships SET payload=? WHERE id=?",
                    (self._dump(revised), relationship_id),
                )
                self._conn.execute(
                    "INSERT INTO relationship_history(relationship_id,revision,transaction_time,valid_from,valid_to,payload) VALUES(?,?,?,?,?,?)",
                    (
                        relationship_id,
                        revision,
                        tx.isoformat(),
                        revised.valid_from.isoformat() if revised.valid_from else None,
                        revised.valid_to.isoformat() if revised.valid_to else None,
                        self._dump(revised),
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            return revised

    def relationships_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        direction: str = "out",
        as_of_transaction: datetime | None = None,
    ) -> list[Relationship]:
        if direction not in {"out", "in"}:
            raise ValueError("direction must be 'out' or 'in'")
        rows = self._conn.execute(
            "SELECT relationship_id,revision,transaction_time,payload FROM relationship_history ORDER BY relationship_id,revision"
        ).fetchall()
        latest: dict[str, tuple[int, datetime, Relationship]] = {}
        tx_limit = _as_utc(as_of_transaction) if as_of_transaction else None
        for row in rows:
            tx = _as_utc(datetime.fromisoformat(row["transaction_time"]))
            if tx_limit is not None and tx > tx_limit:
                continue
            rel = Relationship.model_validate_json(row["payload"])
            revision = int(row["revision"])
            existing = latest.get(row["relationship_id"])
            if existing is None or (tx, revision) > (existing[1], existing[0]):
                latest[row["relationship_id"]] = (revision, tx, rel)
        result = []
        for _, _, rel in latest.values():
            endpoint = rel.source.id if direction == "out" else rel.target.id
            if endpoint == object_id and _contains(valid_time, rel.valid_from, rel.valid_to):
                result.append(rel)
        return sorted(result, key=lambda r: r.id)

    def events_for(self, object_id: str):
        rows = self._conn.execute(
            "SELECT payload FROM events WHERE subject_id=? ORDER BY occurred_at,id", (object_id,)
        ).fetchall()
        from .model import OperationalEvent

        return [OperationalEvent.model_validate_json(row["payload"]) for row in rows]
