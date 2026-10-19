"""Durable, version-pinned registry for CEPIO Performance Contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from .model import utcnow
from .performance_contract import PerformanceContract
from .performance_resolution import (
    PerformanceContractDefinition,
    PerformanceContractOverlay,
    PerformanceContractResolutionError,
    PerformanceContractResolver,
    ResolvedPerformanceContract,
)


class PerformanceContractLifecycle(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"


class PerformanceContractRevisionRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_id: str
    version: str
    definition_hash: str


class PerformanceContractRevision(BaseModel):
    """Immutable contract payload plus mutable lifecycle metadata."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    version: str
    definition: PerformanceContractDefinition
    definition_hash: str
    lifecycle: PerformanceContractLifecycle = PerformanceContractLifecycle.draft
    parent_revision: PerformanceContractRevisionRef | None = None
    effective_organization_id: str | None = None
    created_at: datetime
    activated_at: datetime | None = None
    retired_at: datetime | None = None

    @property
    def ref(self) -> PerformanceContractRevisionRef:
        return PerformanceContractRevisionRef(
            contract_id=self.contract_id,
            version=self.version,
            definition_hash=self.definition_hash,
        )


class RegisteredPerformanceContractResolution(BaseModel):
    model_config = ConfigDict(frozen=True)

    resolved: ResolvedPerformanceContract
    source_revisions: tuple[PerformanceContractRevisionRef, ...]


class PerformanceContractRegistryError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PerformanceContractStore(Protocol):
    def create(self, revision: PerformanceContractRevision) -> None: ...
    def get(self, contract_id: str, version: str) -> PerformanceContractRevision | None: ...
    def get_active(self, contract_id: str) -> PerformanceContractRevision | None: ...
    def list(self, contract_id: str | None = None) -> list[PerformanceContractRevision]: ...
    def activate(
        self, contract_id: str, version: str, *, activated_at: datetime
    ) -> PerformanceContractRevision: ...
    def retire(
        self, contract_id: str, version: str, *, retired_at: datetime
    ) -> PerformanceContractRevision: ...


class InMemoryPerformanceContractStore(PerformanceContractStore):
    def __init__(self) -> None:
        self._revisions: dict[tuple[str, str], PerformanceContractRevision] = {}
        self._lock = RLock()

    def create(self, revision: PerformanceContractRevision) -> None:
        key = (revision.contract_id, revision.version)
        with self._lock:
            if key in self._revisions:
                raise ValueError(f"Performance contract revision already exists: {key}")
            self._revisions[key] = revision.model_copy(deep=True)

    def get(self, contract_id: str, version: str) -> PerformanceContractRevision | None:
        with self._lock:
            item = self._revisions.get((contract_id, version))
            return item.model_copy(deep=True) if item else None

    def get_active(self, contract_id: str) -> PerformanceContractRevision | None:
        with self._lock:
            for item in self._revisions.values():
                if item.contract_id == contract_id and item.lifecycle == PerformanceContractLifecycle.active:
                    return item.model_copy(deep=True)
        return None

    def list(self, contract_id: str | None = None) -> list[PerformanceContractRevision]:
        with self._lock:
            items = [
                item.model_copy(deep=True)
                for item in self._revisions.values()
                if contract_id is None or item.contract_id == contract_id
            ]
        return sorted(items, key=lambda item: (item.contract_id, item.created_at, item.version))

    def activate(
        self, contract_id: str, version: str, *, activated_at: datetime
    ) -> PerformanceContractRevision:
        key = (contract_id, version)
        with self._lock:
            target = self._revisions.get(key)
            if target is None:
                raise KeyError(key)
            if target.lifecycle == PerformanceContractLifecycle.retired:
                raise ValueError("Retired performance contract revisions cannot be reactivated")
            if target.lifecycle == PerformanceContractLifecycle.active:
                return target.model_copy(deep=True)
            for other_key, item in tuple(self._revisions.items()):
                if item.contract_id == contract_id and item.lifecycle == PerformanceContractLifecycle.active:
                    self._revisions[other_key] = item.model_copy(
                        update={
                            "lifecycle": PerformanceContractLifecycle.retired,
                            "retired_at": activated_at,
                        }
                    )
            activated = target.model_copy(
                update={
                    "lifecycle": PerformanceContractLifecycle.active,
                    "activated_at": activated_at,
                    "retired_at": None,
                }
            )
            self._revisions[key] = activated
            return activated.model_copy(deep=True)

    def retire(
        self, contract_id: str, version: str, *, retired_at: datetime
    ) -> PerformanceContractRevision:
        key = (contract_id, version)
        with self._lock:
            target = self._revisions.get(key)
            if target is None:
                raise KeyError(key)
            if target.lifecycle == PerformanceContractLifecycle.retired:
                return target.model_copy(deep=True)
            retired = target.model_copy(
                update={"lifecycle": PerformanceContractLifecycle.retired, "retired_at": retired_at}
            )
            self._revisions[key] = retired
            return retired.model_copy(deep=True)


class SQLitePerformanceContractStore(PerformanceContractStore):
    """SQLite reference backend preserving immutable revision payloads."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def close(self) -> None:
        self._conn.close()

    def _initialize(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS performance_contract_revisions (
                    contract_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    definition_type TEXT NOT NULL,
                    definition_json TEXT NOT NULL,
                    definition_hash TEXT NOT NULL,
                    lifecycle TEXT NOT NULL,
                    parent_contract_id TEXT,
                    parent_version TEXT,
                    parent_hash TEXT,
                    effective_organization_id TEXT,
                    created_at TEXT NOT NULL,
                    activated_at TEXT,
                    retired_at TEXT,
                    PRIMARY KEY (contract_id, version)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS ux_performance_contract_active
                ON performance_contract_revisions(contract_id)
                WHERE lifecycle = 'active';
                CREATE INDEX IF NOT EXISTS ix_performance_contract_org
                ON performance_contract_revisions(effective_organization_id, contract_id);
                """
            )
            self._conn.commit()

    def create(self, revision: PerformanceContractRevision) -> None:
        definition_type = (
            "overlay" if isinstance(revision.definition, PerformanceContractOverlay) else "complete"
        )
        parent = revision.parent_revision
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    """
                    INSERT INTO performance_contract_revisions (
                        contract_id, version, definition_type, definition_json,
                        definition_hash, lifecycle, parent_contract_id, parent_version,
                        parent_hash, effective_organization_id, created_at,
                        activated_at, retired_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.contract_id,
                        revision.version,
                        definition_type,
                        revision.definition.model_dump_json(),
                        revision.definition_hash,
                        revision.lifecycle.value,
                        parent.contract_id if parent else None,
                        parent.version if parent else None,
                        parent.definition_hash if parent else None,
                        revision.effective_organization_id,
                        revision.created_at.isoformat(),
                        revision.activated_at.isoformat() if revision.activated_at else None,
                        revision.retired_at.isoformat() if revision.retired_at else None,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Performance contract revision already exists: "
                    f"{revision.contract_id}@{revision.version}"
                ) from exc

    def get(self, contract_id: str, version: str) -> PerformanceContractRevision | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM performance_contract_revisions WHERE contract_id = ? AND version = ?",
                (contract_id, version),
            ).fetchone()
        return self._from_row(row) if row else None

    def get_active(self, contract_id: str) -> PerformanceContractRevision | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM performance_contract_revisions
                   WHERE contract_id = ? AND lifecycle = 'active'""",
                (contract_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list(self, contract_id: str | None = None) -> list[PerformanceContractRevision]:
        with self._lock:
            if contract_id is None:
                rows = self._conn.execute(
                    """SELECT * FROM performance_contract_revisions
                       ORDER BY contract_id, created_at, version"""
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """SELECT * FROM performance_contract_revisions
                       WHERE contract_id = ? ORDER BY created_at, version""",
                    (contract_id,),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def activate(
        self, contract_id: str, version: str, *, activated_at: datetime
    ) -> PerformanceContractRevision:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT lifecycle FROM performance_contract_revisions WHERE contract_id = ? AND version = ?",
                (contract_id, version),
            ).fetchone()
            if row is None:
                raise KeyError((contract_id, version))
            lifecycle = PerformanceContractLifecycle(row["lifecycle"])
            if lifecycle == PerformanceContractLifecycle.retired:
                raise ValueError("Retired performance contract revisions cannot be reactivated")
            if lifecycle != PerformanceContractLifecycle.active:
                self._conn.execute(
                    """UPDATE performance_contract_revisions
                       SET lifecycle = 'retired', retired_at = ?
                       WHERE contract_id = ? AND lifecycle = 'active'""",
                    (activated_at.isoformat(), contract_id),
                )
                self._conn.execute(
                    """UPDATE performance_contract_revisions
                       SET lifecycle = 'active', activated_at = ?, retired_at = NULL
                       WHERE contract_id = ? AND version = ?""",
                    (activated_at.isoformat(), contract_id, version),
                )
        result = self.get(contract_id, version)
        assert result is not None
        return result

    def retire(
        self, contract_id: str, version: str, *, retired_at: datetime
    ) -> PerformanceContractRevision:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT lifecycle FROM performance_contract_revisions WHERE contract_id = ? AND version = ?",
                (contract_id, version),
            ).fetchone()
            if row is None:
                raise KeyError((contract_id, version))
            if PerformanceContractLifecycle(row["lifecycle"]) != PerformanceContractLifecycle.retired:
                self._conn.execute(
                    """UPDATE performance_contract_revisions
                       SET lifecycle = 'retired', retired_at = ?
                       WHERE contract_id = ? AND version = ?""",
                    (retired_at.isoformat(), contract_id, version),
                )
        result = self.get(contract_id, version)
        assert result is not None
        return result

    @staticmethod
    def _from_row(row: sqlite3.Row) -> PerformanceContractRevision:
        payload = json.loads(row["definition_json"])
        definition: PerformanceContractDefinition
        if row["definition_type"] == "overlay":
            definition = PerformanceContractOverlay.model_validate(payload)
        else:
            definition = PerformanceContract.model_validate(payload)
        parent = None
        if row["parent_contract_id"] is not None:
            parent = PerformanceContractRevisionRef(
                contract_id=row["parent_contract_id"],
                version=row["parent_version"],
                definition_hash=row["parent_hash"],
            )
        return PerformanceContractRevision(
            contract_id=row["contract_id"],
            version=row["version"],
            definition=definition,
            definition_hash=row["definition_hash"],
            lifecycle=PerformanceContractLifecycle(row["lifecycle"]),
            parent_revision=parent,
            effective_organization_id=row["effective_organization_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            activated_at=(
                datetime.fromisoformat(row["activated_at"]) if row["activated_at"] else None
            ),
            retired_at=datetime.fromisoformat(row["retired_at"]) if row["retired_at"] else None,
        )


class PerformanceContractRegistry:
    """Versioned lifecycle and deterministic resolution for Performance Contracts."""

    def __init__(self, store: PerformanceContractStore | None = None) -> None:
        self.store = store or InMemoryPerformanceContractStore()

    def register(
        self,
        definition: PerformanceContractDefinition,
        *,
        parent_version: str | None = None,
        activate: bool = False,
        created_at: datetime | None = None,
    ) -> PerformanceContractRevision:
        if self.store.get(definition.id, definition.version) is not None:
            raise PerformanceContractRegistryError(
                "REVISION_ALREADY_EXISTS",
                f"Performance contract revision already exists: {definition.id}@{definition.version}",
            )

        parent_ref = self._select_parent(definition, parent_version)
        timestamp = created_at or utcnow()
        draft = PerformanceContractRevision(
            contract_id=definition.id,
            version=definition.version,
            definition=definition,
            definition_hash=_definition_hash(definition),
            parent_revision=parent_ref,
            created_at=timestamp,
        )
        validated = self._resolution_for_revision(draft)
        draft = draft.model_copy(
            update={"effective_organization_id": validated.resolved.contract.organization_id}
        )
        self.store.create(draft)
        return self.activate(definition.id, definition.version, activated_at=timestamp) if activate else draft

    def get(self, contract_id: str, version: str) -> PerformanceContractRevision:
        revision = self.store.get(contract_id, version)
        if revision is None:
            raise PerformanceContractRegistryError(
                "REVISION_NOT_FOUND",
                f"Performance contract revision not found: {contract_id}@{version}",
            )
        return revision

    def get_active(self, contract_id: str) -> PerformanceContractRevision:
        revision = self.store.get_active(contract_id)
        if revision is None:
            raise PerformanceContractRegistryError(
                "ACTIVE_REVISION_NOT_FOUND",
                f"No active performance contract revision: {contract_id}",
            )
        return revision

    def list_versions(self, contract_id: str) -> tuple[PerformanceContractRevision, ...]:
        return tuple(self.store.list(contract_id))

    def list_for_organization(
        self, organization_id: str, *, include_industry_reference: bool = False
    ) -> tuple[PerformanceContractRevision, ...]:
        return tuple(
            revision
            for revision in self.store.list()
            if revision.effective_organization_id == organization_id
            or (include_industry_reference and revision.effective_organization_id is None)
        )

    def activate(
        self, contract_id: str, version: str, *, activated_at: datetime | None = None
    ) -> PerformanceContractRevision:
        revision = self.get(contract_id, version)
        if revision.lifecycle == PerformanceContractLifecycle.retired:
            raise PerformanceContractRegistryError(
                "REVISION_RETIRED",
                f"Retired performance contract revision cannot be activated: {contract_id}@{version}",
            )
        self._resolution_for_revision(revision)
        return self.store.activate(contract_id, version, activated_at=activated_at or utcnow())

    def retire(
        self, contract_id: str, version: str, *, retired_at: datetime | None = None
    ) -> PerformanceContractRevision:
        self.get(contract_id, version)
        return self.store.retire(contract_id, version, retired_at=retired_at or utcnow())

    def resolve(
        self,
        contract_id: str,
        version: str | None = None,
        *,
        organization_id: str | None = None,
    ) -> RegisteredPerformanceContractResolution:
        revision = self.get(contract_id, version) if version else self.get_active(contract_id)
        result = self._resolution_for_revision(revision)
        effective_org = result.resolved.contract.organization_id
        if organization_id is not None and effective_org != organization_id:
            raise PerformanceContractRegistryError(
                "ORGANIZATION_SCOPE_MISMATCH",
                f"Performance contract {contract_id}@{revision.version} is scoped to "
                f"{effective_org!r}, not {organization_id!r}",
            )
        return result

    def _select_parent(
        self, definition: PerformanceContractDefinition, parent_version: str | None
    ) -> PerformanceContractRevisionRef | None:
        parent_id = definition.extends_contract_id
        if parent_id is None:
            if parent_version is not None:
                raise PerformanceContractRegistryError(
                    "UNEXPECTED_PARENT_VERSION",
                    "parent_version is valid only for a contract that extends another contract",
                )
            return None
        if parent_version is None:
            parent = self.store.get_active(parent_id)
            if parent is None:
                raise PerformanceContractRegistryError(
                    "ACTIVE_PARENT_NOT_FOUND",
                    f"No active parent revision for performance contract: {parent_id}",
                )
        else:
            parent = self.store.get(parent_id, parent_version)
            if parent is None:
                raise PerformanceContractRegistryError(
                    "PARENT_REVISION_NOT_FOUND",
                    f"Parent performance contract revision not found: {parent_id}@{parent_version}",
                )
        return parent.ref

    def _resolution_for_revision(
        self, leaf: PerformanceContractRevision
    ) -> RegisteredPerformanceContractResolution:
        chain = self._revision_chain(leaf)
        try:
            resolved = PerformanceContractResolver(
                tuple(revision.definition for revision in chain)
            ).resolve(leaf.contract_id)
        except PerformanceContractResolutionError as exc:
            raise PerformanceContractRegistryError(exc.code, str(exc)) from exc
        return RegisteredPerformanceContractResolution(
            resolved=resolved,
            source_revisions=tuple(revision.ref for revision in chain),
        )

    def _revision_chain(
        self, leaf: PerformanceContractRevision
    ) -> list[PerformanceContractRevision]:
        chain = [leaf]
        seen = {leaf.contract_id}
        cursor = leaf
        while cursor.parent_revision is not None:
            parent_ref = cursor.parent_revision
            if parent_ref.contract_id in seen:
                raise PerformanceContractRegistryError(
                    "INHERITANCE_CYCLE",
                    f"Performance contract revision chain cycles at {parent_ref.contract_id}",
                )
            parent = self.store.get(parent_ref.contract_id, parent_ref.version)
            if parent is None:
                raise PerformanceContractRegistryError(
                    "PINNED_PARENT_NOT_FOUND",
                    f"Pinned parent revision not found: "
                    f"{parent_ref.contract_id}@{parent_ref.version}",
                )
            if parent.definition_hash != parent_ref.definition_hash:
                raise PerformanceContractRegistryError(
                    "PINNED_PARENT_HASH_MISMATCH",
                    f"Pinned parent revision hash changed: "
                    f"{parent_ref.contract_id}@{parent_ref.version}",
                )
            seen.add(parent.contract_id)
            chain.append(parent)
            cursor = parent
        chain.reverse()
        return chain


def _definition_hash(definition: PerformanceContractDefinition) -> str:
    payload = json.dumps(
        definition.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()
