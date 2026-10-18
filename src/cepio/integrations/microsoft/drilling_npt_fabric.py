from __future__ import annotations

from typing import Any, Protocol

from ...domain_bindings import ExternalRecordReference
from ...drilling_npt_binding import (
    DrillingNPTActivityEvidence,
    DrillingNPTContextEvidence,
)
from ...platform_bindings import (
    BindingCapability,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
)


class FabricDrillingNPTTableReader(Protocol):
    """Narrow transport seam for normalized Fabric rows.

    Authentication, SQL/KQL transport and workspace lifecycle are intentionally outside
    this contract. A live transport can implement the reader without changing Drilling
    Industry IQ or the CEPIO operating contract.
    """

    def read_rows(self, table_name: str, *, context_id: str) -> list[dict[str, Any]]: ...


class FabricDrillingNPTBinding:
    """Resolve normalized Microsoft Fabric rows into drilling NPT evidence.

    The binding knows Fabric-shaped table columns; CEPIO Core does not. It emits only
    the thin provider-neutral evidence projection consumed by Drilling Industry IQ.
    """

    manifest = PlatformBindingManifest(
        binding_id="cepio.binding.microsoft-fabric.drilling-npt",
        provider_id="microsoft-fabric",
        source_system="microsoft-fabric",
        mode=BindingMode.evidence,
        capabilities=frozenset(
            {
                BindingCapability.resolve_evidence,
                BindingCapability.versioned_identity,
            }
        ),
    )

    def __init__(
        self,
        reader: FabricDrillingNPTTableReader,
        *,
        dataset_id: str | None = None,
        context_table: str = "cepio_drilling_npt_context",
        activity_table: str = "cepio_drilling_activity_interval",
        classification_table: str = "cepio_drilling_activity_classification",
    ) -> None:
        self.reader = reader
        self.dataset_id = dataset_id
        self.context_table = context_table
        self.activity_table = activity_table
        self.classification_table = classification_table

    def _reference(
        self,
        *,
        record_kind: str,
        record_id: object,
        record_version: object,
        table_name: str,
    ) -> ExternalRecordReference:
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"{table_name} row is missing source_record_id")
        if record_version is None or str(record_version).strip() == "":
            raise ValueError(
                f"{table_name} row {record_id!r} is missing source_record_version"
            )
        return ExternalRecordReference(
            source_system=self.manifest.source_system,
            record_kind=record_kind,
            record_id=record_id,
            source_service="FabricTableReader",
            record_version=str(record_version),
            dataset_id=self.dataset_id,
            metadata={"table": table_name},
        )

    @staticmethod
    def _one(rows: list[dict[str, Any]], *, label: str, context_id: str) -> dict[str, Any]:
        if not rows:
            raise KeyError(f"No {label} row found for drilling NPT context {context_id}")
        if len(rows) != 1:
            raise ValueError(
                f"Expected exactly one {label} row for drilling NPT context {context_id}; "
                f"found {len(rows)}"
            )
        return rows[0]

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        context_row = self._one(
            self.reader.read_rows(self.context_table, context_id=external_id),
            label="context",
            context_id=external_id,
        )
        activity_rows = self.reader.read_rows(self.activity_table, context_id=external_id)
        if not activity_rows:
            raise ValueError(f"Drilling NPT context {external_id} contains no activity rows")
        classification_rows = self.reader.read_rows(
            self.classification_table,
            context_id=external_id,
        )

        context_reference = self._reference(
            record_kind="drilling-npt-context",
            record_id=context_row.get("source_record_id"),
            record_version=context_row.get("source_record_version"),
            table_name=self.context_table,
        )
        if context_reference.record_id != external_id:
            raise ValueError(
                "Fabric drilling NPT context source_record_id must equal the requested context_id"
            )

        classifications_by_activity: dict[str, list[dict[str, Any]]] = {}
        for row in classification_rows:
            activity_id = row.get("activity_id")
            if isinstance(activity_id, str):
                classifications_by_activity.setdefault(activity_id, []).append(row)

        known_activity_ids = {str(row.get("activity_id")) for row in activity_rows}
        orphan_ids = sorted(set(classifications_by_activity) - known_activity_ids)
        if orphan_ids:
            raise ValueError(
                f"Fabric drilling NPT context {external_id} has orphan classifications: {orphan_ids}"
            )

        activities: list[DrillingNPTActivityEvidence] = []
        for row in activity_rows:
            activity_id = row.get("activity_id")
            if not isinstance(activity_id, str) or not activity_id.strip():
                raise ValueError(f"{self.activity_table} row is missing activity_id")
            matches = classifications_by_activity.get(activity_id, [])
            if not matches:
                raise ValueError(
                    f"Activity {activity_id} has no Fabric drilling activity classification"
                )
            if len(matches) != 1:
                raise ValueError(
                    f"Activity {activity_id} has {len(matches)} Fabric classifications; expected one"
                )
            classification = matches[0]
            productive = classification.get("is_productive")
            if not isinstance(productive, bool):
                raise ValueError(
                    f"Activity {activity_id} classification is_productive must be boolean"
                )

            activities.append(
                DrillingNPTActivityEvidence(
                    activity_id=activity_id,
                    activity_name=str(row.get("activity_name") or activity_id),
                    start_time=str(row.get("start_time") or ""),
                    end_time=str(row.get("end_time") or ""),
                    classification_id=str(
                        classification.get("classification_id")
                        or f"CLASS-{activity_id}"
                    ),
                    classification_name=str(
                        classification.get("classification_name") or "Drilling classification"
                    ),
                    is_productive=productive,
                    activity_reference=self._reference(
                        record_kind="drilling-activity-interval",
                        record_id=row.get("source_record_id"),
                        record_version=row.get("source_record_version"),
                        table_name=self.activity_table,
                    ),
                    classification_reference=self._reference(
                        record_kind="drilling-activity-classification",
                        record_id=classification.get("source_record_id"),
                        record_version=classification.get("source_record_version"),
                        table_name=self.classification_table,
                    ),
                )
            )

        context = DrillingNPTContextEvidence(
            context_id=external_id,
            context_reference=context_reference,
            rig_id=str(context_row.get("rig_id") or ""),
            rig_name=str(context_row.get("rig_name") or context_row.get("rig_id") or ""),
            rig_reference=self._reference(
                record_kind="operating-rig",
                record_id=context_row.get("rig_source_record_id"),
                record_version=context_row.get("rig_source_record_version"),
                table_name=self.context_table,
            ),
            well_id=str(context_row.get("well_id") or ""),
            well_name=str(context_row.get("well_name") or context_row.get("well_id") or ""),
            well_reference=self._reference(
                record_kind="well",
                record_id=context_row.get("well_source_record_id"),
                record_version=context_row.get("well_source_record_version"),
                table_name=self.context_table,
            ),
            activities=activities,
        )
        if not context.rig_id or not context.well_id:
            raise ValueError(
                f"Fabric drilling NPT context {external_id} must resolve rig_id and well_id"
            )

        return EvidenceEnvelope(
            reference=context.context_reference,
            evidence=context.model_dump(mode="json"),
        )
