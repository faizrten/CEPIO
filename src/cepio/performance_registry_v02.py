"""Additive durable store support for Performance Contract specialization v0.2.

The v0.1 registry/store module remains byte-stable. This store extends only the SQLite
serialization boundary so v0.2 sparse overlays retain patch/suppression semantics
across process restarts.
"""

from __future__ import annotations

import json
import sqlite3

from .performance_contract import PerformanceContract
from .performance_registry import (
    PerformanceContractLifecycle,
    PerformanceContractRevision,
    PerformanceContractRevisionRef,
    SQLitePerformanceContractStore,
)
from .performance_resolution import PerformanceContractOverlay
from .performance_resolution import PerformanceContractOverlayV2


class SQLitePerformanceContractStoreV2(SQLitePerformanceContractStore):
    """SQLite store that round-trips v0.1 and v0.2 Performance Contract overlays."""

    def create(self, revision: PerformanceContractRevision) -> None:
        if not isinstance(revision.definition, PerformanceContractOverlayV2):
            super().create(revision)
            return

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
                        "overlay_v2",
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
                    "Performance contract revision already exists: "
                    f"{revision.contract_id}@{revision.version}"
                ) from exc

    @staticmethod
    def _from_row(row: sqlite3.Row) -> PerformanceContractRevision:
        if row["definition_type"] != "overlay_v2":
            return SQLitePerformanceContractStore._from_row(row)

        payload = json.loads(row["definition_json"])
        definition = PerformanceContractOverlayV2.model_validate(payload)
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
            created_at=SQLitePerformanceContractStoreV2._parse_datetime(row["created_at"]),
            activated_at=(
                SQLitePerformanceContractStoreV2._parse_datetime(row["activated_at"])
                if row["activated_at"]
                else None
            ),
            retired_at=(
                SQLitePerformanceContractStoreV2._parse_datetime(row["retired_at"])
                if row["retired_at"]
                else None
            ),
        )

    @staticmethod
    def _parse_datetime(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)


__all__ = [
    "PerformanceContract",
    "PerformanceContractOverlay",
    "PerformanceContractOverlayV2",
    "SQLitePerformanceContractStoreV2",
]
