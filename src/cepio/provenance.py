from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from cepio.model import utcnow
from cepio.property_registry import PropertyRegistry


class SourceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_system: str
    source_entity: str
    source_field: str
    source_record_id: str | None = None
    source_uri: str | None = None


class TransformationRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    mapping_id: str
    mapping_version: str
    code_version: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PropertyProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    object_id: str
    property_iri: str
    source: SourceReference
    mapping_kind: str
    mapping_version: str
    ingested_at: datetime = Field(default_factory=utcnow)
    observed_at: datetime | None = None
    transformation_id: str | None = None
    source_value_hash: str | None = None

    @classmethod
    def create(
        cls,
        *,
        object_id: str,
        property_name: str,
        property_registry: PropertyRegistry,
        source: SourceReference,
        mapping_kind: str,
        mapping_version: str,
        observed_at: datetime | None = None,
        transformation_id: str | None = None,
        source_value: Any | None = None,
    ) -> "PropertyProvenance":
        definition = property_registry.resolve(property_name)
        value_hash = None
        if source_value is not None:
            serialized = json.dumps(source_value, sort_keys=True, default=str, separators=(",", ":"))
            value_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return cls(
            object_id=object_id,
            property_iri=definition.iri,
            source=source,
            mapping_kind=mapping_kind,
            mapping_version=mapping_version,
            observed_at=observed_at,
            transformation_id=transformation_id,
            source_value_hash=value_hash,
        )


class ProvenanceRepository(Protocol):
    def append_property(self, record: PropertyProvenance) -> None: ...
    def list_for_property(self, object_id: str, property_iri: str) -> list[PropertyProvenance]: ...
    def add_transformation(self, run: TransformationRun) -> None: ...
    def get_transformation(self, transformation_id: str) -> TransformationRun | None: ...


class InMemoryProvenanceRepository:
    def __init__(self) -> None:
        self.property_records: list[PropertyProvenance] = []
        self.transformations: dict[str, TransformationRun] = {}

    def append_property(self, record: PropertyProvenance) -> None:
        self.property_records.append(record)

    def list_for_property(self, object_id: str, property_iri: str) -> list[PropertyProvenance]:
        return [
            record
            for record in self.property_records
            if record.object_id == object_id and record.property_iri == property_iri
        ]

    def add_transformation(self, run: TransformationRun) -> None:
        self.transformations[run.id] = run

    def get_transformation(self, transformation_id: str) -> TransformationRun | None:
        return self.transformations.get(transformation_id)


class SQLiteProvenanceRepository:
    """Reference persistent provenance store.

    This is deliberately independent of a specific enterprise lineage product. Purview,
    Fabric or another lineage backend can implement the same repository contract.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cepio_property_provenance (
                id TEXT PRIMARY KEY,
                object_id TEXT NOT NULL,
                property_iri TEXT NOT NULL,
                source_json TEXT NOT NULL,
                mapping_kind TEXT NOT NULL,
                mapping_version TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                observed_at TEXT,
                transformation_id TEXT,
                source_value_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_cepio_property_provenance_lookup
                ON cepio_property_provenance(object_id, property_iri, ingested_at);
            CREATE TABLE IF NOT EXISTS cepio_transformation_runs (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def append_property(self, record: PropertyProvenance) -> None:
        self.connection.execute(
            """
            INSERT INTO cepio_property_provenance (
                id, object_id, property_iri, source_json, mapping_kind, mapping_version,
                ingested_at, observed_at, transformation_id, source_value_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.object_id,
                record.property_iri,
                record.source.model_dump_json(),
                record.mapping_kind,
                record.mapping_version,
                record.ingested_at.isoformat(),
                record.observed_at.isoformat() if record.observed_at else None,
                record.transformation_id,
                record.source_value_hash,
            ),
        )
        self.connection.commit()

    def list_for_property(self, object_id: str, property_iri: str) -> list[PropertyProvenance]:
        rows = self.connection.execute(
            """
            SELECT * FROM cepio_property_provenance
            WHERE object_id = ? AND property_iri = ?
            ORDER BY ingested_at ASC, id ASC
            """,
            (object_id, property_iri),
        ).fetchall()
        records: list[PropertyProvenance] = []
        for row in rows:
            records.append(
                PropertyProvenance(
                    id=row["id"],
                    object_id=row["object_id"],
                    property_iri=row["property_iri"],
                    source=SourceReference.model_validate_json(row["source_json"]),
                    mapping_kind=row["mapping_kind"],
                    mapping_version=row["mapping_version"],
                    ingested_at=datetime.fromisoformat(row["ingested_at"]),
                    observed_at=datetime.fromisoformat(row["observed_at"]) if row["observed_at"] else None,
                    transformation_id=row["transformation_id"],
                    source_value_hash=row["source_value_hash"],
                )
            )
        return records

    def add_transformation(self, run: TransformationRun) -> None:
        self.connection.execute(
            "INSERT INTO cepio_transformation_runs(id, payload_json) VALUES (?, ?)",
            (run.id, run.model_dump_json()),
        )
        self.connection.commit()

    def get_transformation(self, transformation_id: str) -> TransformationRun | None:
        row = self.connection.execute(
            "SELECT payload_json FROM cepio_transformation_runs WHERE id = ?",
            (transformation_id,),
        ).fetchone()
        return TransformationRun.model_validate_json(row["payload_json"]) if row else None

    def close(self) -> None:
        self.connection.close()


def explain_property(
    object_id: str,
    property_name: str,
    property_registry: PropertyRegistry,
    repository: ProvenanceRepository,
) -> dict[str, Any]:
    definition = property_registry.resolve(property_name)
    records = repository.list_for_property(object_id, definition.iri)
    transformations: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.transformation_id and record.transformation_id not in transformations:
            run = repository.get_transformation(record.transformation_id)
            if run:
                transformations[run.id] = run.model_dump(mode="json")
    return {
        "object_id": object_id,
        "property": {
            "qname": definition.qname,
            "iri": definition.iri,
            "datatype": definition.datatype,
            "authority": definition.authority,
        },
        "provenance": [record.model_dump(mode="json") for record in records],
        "transformations": transformations,
    }
