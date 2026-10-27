"""CEPIO durable-memory contracts and bounded working-context assembly."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryKind(str, Enum):
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    EPISODIC = "EPISODIC"
    PROFILE = "PROFILE"


class MemoryScope(str, Enum):
    GLOBAL = "GLOBAL"
    TENANT = "TENANT"
    PROFILE = "PROFILE"


class ContextStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class MemoryAccessError(PermissionError):
    """Raised when a tenant attempts to access or mutate another tenant's memory."""


class MemoryBoundaryError(ValueError):
    """Raised when a memory mutation would cross its durable ownership boundary."""


class MemoryProvenance(BaseModel):
    source_kind: str
    source_ids: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    customer_specific: bool = False


class MemoryReference(BaseModel):
    source_system: str
    resource_type: str
    resource_id: str
    binding: str | None = None
    observed_at: datetime | None = None
    content_hash: str | None = None


class MemoryRecord(BaseModel):
    id: str
    kind: MemoryKind
    scope: MemoryScope
    summary: str
    provenance: MemoryProvenance
    tenant_id: str | None = None
    sovereignty_source_id: str | None = None
    reference: MemoryReference | None = None
    classification: str = "internal"
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    capability_ids: set[str] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_boundary(self) -> "MemoryRecord":
        if self.scope == MemoryScope.GLOBAL:
            if self.tenant_id is not None or self.provenance.customer_specific:
                raise ValueError("global memory cannot contain tenant/customer-specific knowledge")
        elif not self.tenant_id:
            raise ValueError("tenant/profile memory requires tenant_id")
        if (self.kind == MemoryKind.PROFILE) != (self.scope == MemoryScope.PROFILE):
            raise ValueError("PROFILE kind and PROFILE scope must be used together")
        if self.sovereignty_source_id is not None and not self.sovereignty_source_id.strip():
            raise ValueError("sovereignty_source_id must be nonblank")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        return self

    def visible_to(self, tenant_id: str | None) -> bool:
        return self.scope == MemoryScope.GLOBAL or self.tenant_id == tenant_id

    def expired_at(self, at: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= at


class MemoryQuery(BaseModel):
    tenant_id: str | None = None
    kinds: set[MemoryKind] = Field(default_factory=set)
    capability_ids: set[str] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)
    include_global: bool = True
    limit: int = Field(default=50, ge=1)
    at: datetime = Field(default_factory=utcnow)


class MemoryStore(Protocol):
    def put(self, record: MemoryRecord) -> MemoryRecord: ...

    def get(self, memory_id: str, tenant_id: str | None = None) -> MemoryRecord | None: ...

    def query(self, query: MemoryQuery) -> list[MemoryRecord]: ...

    def forget(self, memory_id: str, tenant_id: str | None = None) -> bool: ...


def _validate_update_boundary(prior: MemoryRecord | None, record: MemoryRecord) -> None:
    if prior and (prior.scope, prior.tenant_id) != (record.scope, record.tenant_id):
        raise MemoryBoundaryError("memory ownership boundary cannot change during update")


def _visible_record(record: MemoryRecord, tenant_id: str | None) -> MemoryRecord | None:
    if not record.visible_to(tenant_id):
        raise MemoryAccessError("memory is outside the requested tenant boundary")
    if record.expired_at(utcnow()):
        return None
    return record.model_copy(deep=True)


def _matches_query(record: MemoryRecord, query: MemoryQuery) -> bool:
    if record.expired_at(query.at):
        return False
    if record.scope == MemoryScope.GLOBAL:
        if not query.include_global:
            return False
    elif record.tenant_id != query.tenant_id:
        return False
    if query.kinds and record.kind not in query.kinds:
        return False
    if query.capability_ids and record.capability_ids.isdisjoint(query.capability_ids):
        return False
    if query.tags and record.tags.isdisjoint(query.tags):
        return False
    return True


def _query_records(records: list[MemoryRecord], query: MemoryQuery) -> list[MemoryRecord]:
    result = [record for record in records if _matches_query(record, query)]
    result.sort(key=lambda item: (-item.created_at.timestamp(), item.id))
    return [item.model_copy(deep=True) for item in result[: query.limit]]


def _can_forget(record: MemoryRecord, tenant_id: str | None) -> bool:
    return (record.scope == MemoryScope.GLOBAL and tenant_id is None) or (
        record.scope != MemoryScope.GLOBAL and record.tenant_id == tenant_id
    )


class InMemoryMemoryStore(MemoryStore):
    """Reference backend for contract tests; production storage is adapter-defined."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}
        self._lock = RLock()

    def put(self, record: MemoryRecord) -> MemoryRecord:
        with self._lock:
            prior = self._records.get(record.id)
            _validate_update_boundary(prior, record)
            stored = record.model_copy(deep=True)
            self._records[record.id] = stored
            return stored.model_copy(deep=True)

    def get(self, memory_id: str, tenant_id: str | None = None) -> MemoryRecord | None:
        record = self._records.get(memory_id)
        if record is None:
            return None
        return _visible_record(record, tenant_id)

    def query(self, query: MemoryQuery) -> list[MemoryRecord]:
        return _query_records(list(self._records.values()), query)

    def forget(self, memory_id: str, tenant_id: str | None = None) -> bool:
        with self._lock:
            record = self._records.get(memory_id)
            if record is None:
                return False
            if not _can_forget(record, tenant_id):
                raise MemoryAccessError("memory deletion is outside the requested tenant boundary")
            del self._records[memory_id]
            return True


class SQLiteMemoryStore(MemoryStore):
    """Durable reference backend proving the memory contract without cloud coupling."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = RLock()
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                scope TEXT NOT NULL,
                tenant_id TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_scope_tenant
                ON memories(scope, tenant_id);
            CREATE INDEX IF NOT EXISTS idx_memory_kind
                ON memories(kind);
            CREATE INDEX IF NOT EXISTS idx_memory_created_at
                ON memories(created_at);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _read(self, memory_id: str) -> MemoryRecord | None:
        row = self._conn.execute(
            "SELECT payload FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return MemoryRecord.model_validate_json(row["payload"]) if row else None

    def put(self, record: MemoryRecord) -> MemoryRecord:
        with self._lock:
            prior = self._read(record.id)
            _validate_update_boundary(prior, record)
            self._conn.execute(
                """
                INSERT INTO memories(id, kind, scope, tenant_id, created_at, expires_at, payload)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    scope=excluded.scope,
                    tenant_id=excluded.tenant_id,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at,
                    payload=excluded.payload
                """,
                (
                    record.id,
                    record.kind.value,
                    record.scope.value,
                    record.tenant_id,
                    record.created_at.isoformat(),
                    record.expires_at.isoformat() if record.expires_at else None,
                    record.model_dump_json(),
                ),
            )
            self._conn.commit()
            return record.model_copy(deep=True)

    def get(self, memory_id: str, tenant_id: str | None = None) -> MemoryRecord | None:
        record = self._read(memory_id)
        if record is None:
            return None
        return _visible_record(record, tenant_id)

    def query(self, query: MemoryQuery) -> list[MemoryRecord]:
        rows = self._conn.execute("SELECT payload FROM memories").fetchall()
        records = [MemoryRecord.model_validate_json(row["payload"]) for row in rows]
        return _query_records(records, query)

    def forget(self, memory_id: str, tenant_id: str | None = None) -> bool:
        with self._lock:
            record = self._read(memory_id)
            if record is None:
                return False
            if not _can_forget(record, tenant_id):
                raise MemoryAccessError("memory deletion is outside the requested tenant boundary")
            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self._conn.commit()
            return True


class ContextBudget(BaseModel):
    max_tokens: int = Field(default=16_000, ge=1)
    max_capabilities: int = Field(default=5, ge=1)
    max_semantic_nodes: int = Field(default=150, ge=0)
    max_evidence_items: int = Field(default=25, ge=0)
    max_episodes: int = Field(default=10, ge=0)


class ContextCandidate(BaseModel):
    record: MemoryRecord
    estimated_tokens: int = Field(ge=1)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    priority: int = 0
    required: bool = False
    semantic_nodes: int = Field(default=0, ge=0)
    evidence_items: int = Field(default=0, ge=0)
    capability_ids: set[str] = Field(default_factory=set)

    def all_capability_ids(self) -> set[str]:
        return self.capability_ids | self.record.capability_ids


class ContextUsage(BaseModel):
    tokens: int = 0
    capabilities: int = 0
    semantic_nodes: int = 0
    evidence_items: int = 0
    episodes: int = 0


class ContextAssemblyResult(BaseModel):
    status: ContextStatus
    selected: list[ContextCandidate]
    dropped_ids: list[str]
    blockers: list[str]
    usage: ContextUsage


class ContextAssembler:
    """Select a deterministic working set that respects explicit context budgets."""

    @staticmethod
    def _rank(candidate: ContextCandidate) -> tuple[bool, int, float, str]:
        return (
            not candidate.required,
            -candidate.priority,
            -candidate.relevance,
            candidate.record.id,
        )

    @staticmethod
    def _overflow_reason(
        candidate: ContextCandidate,
        *,
        budget: ContextBudget,
        usage: ContextUsage,
        capability_ids: set[str],
    ) -> str | None:
        new_capabilities = capability_ids | candidate.all_capability_ids()
        if usage.tokens + candidate.estimated_tokens > budget.max_tokens:
            return "tokens"
        if len(new_capabilities) > budget.max_capabilities:
            return "capabilities"
        if usage.semantic_nodes + candidate.semantic_nodes > budget.max_semantic_nodes:
            return "semantic_nodes"
        if usage.evidence_items + candidate.evidence_items > budget.max_evidence_items:
            return "evidence_items"
        episode_increment = int(candidate.record.kind == MemoryKind.EPISODIC)
        if usage.episodes + episode_increment > budget.max_episodes:
            return "episodes"
        return None

    @staticmethod
    def _add(
        candidate: ContextCandidate,
        usage: ContextUsage,
        capability_ids: set[str],
    ) -> tuple[ContextUsage, set[str]]:
        updated_capabilities = capability_ids | candidate.all_capability_ids()
        return (
            ContextUsage(
                tokens=usage.tokens + candidate.estimated_tokens,
                capabilities=len(updated_capabilities),
                semantic_nodes=usage.semantic_nodes + candidate.semantic_nodes,
                evidence_items=usage.evidence_items + candidate.evidence_items,
                episodes=usage.episodes + int(candidate.record.kind == MemoryKind.EPISODIC),
            ),
            updated_capabilities,
        )

    def assemble(
        self,
        candidates: list[ContextCandidate],
        *,
        tenant_id: str | None,
        budget: ContextBudget,
        at: datetime | None = None,
    ) -> ContextAssemblyResult:
        effective_at = at or utcnow()
        ranked = sorted(candidates, key=self._rank)
        eligible: list[ContextCandidate] = []
        dropped: list[str] = []
        seen: set[str] = set()
        for candidate in ranked:
            memory_id = candidate.record.id
            if memory_id in seen:
                dropped.append(memory_id)
                continue
            seen.add(memory_id)
            if not candidate.record.visible_to(tenant_id) or candidate.record.expired_at(
                effective_at
            ):
                dropped.append(memory_id)
                continue
            eligible.append(candidate)

        selected: list[ContextCandidate] = []
        usage = ContextUsage()
        capability_ids: set[str] = set()
        required = [item for item in eligible if item.required]
        optional = [item for item in eligible if not item.required]
        for candidate in required:
            reason = self._overflow_reason(
                candidate, budget=budget, usage=usage, capability_ids=capability_ids
            )
            if reason:
                blockers = [f"required memory {candidate.record.id} exceeds {reason} budget"]
                dropped.extend(item.record.id for item in eligible)
                return ContextAssemblyResult(
                    status=ContextStatus.BLOCKED,
                    selected=[],
                    dropped_ids=sorted(set(dropped)),
                    blockers=blockers,
                    usage=ContextUsage(),
                )
            usage, capability_ids = self._add(candidate, usage, capability_ids)
            selected.append(candidate)

        for candidate in optional:
            reason = self._overflow_reason(
                candidate, budget=budget, usage=usage, capability_ids=capability_ids
            )
            if reason:
                dropped.append(candidate.record.id)
                continue
            usage, capability_ids = self._add(candidate, usage, capability_ids)
            selected.append(candidate)

        return ContextAssemblyResult(
            status=ContextStatus.READY,
            selected=selected,
            dropped_ids=sorted(set(dropped)),
            blockers=[],
            usage=usage,
        )
