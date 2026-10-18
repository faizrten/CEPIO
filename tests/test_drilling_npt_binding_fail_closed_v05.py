from __future__ import annotations

import pytest

from cepio.domain_bindings import ExternalRecordReference
from cepio.drilling_npt_binding import (
    DrillingNPTActivityEvidence,
    DrillingNPTContextEvidence,
    qualify_drilling_npt_binding,
)
from cepio.integrations.microsoft.drilling_npt_fabric import FabricDrillingNPTBinding
from cepio.integrations.synthetic.drilling_npt import SyntheticDrillingNPTBinding
from cepio.platform_bindings import EvidenceEnvelope


CONTEXT_ID = "NPT-CONTEXT-001"
SOURCE = "synthetic-drilling"


def _ref(
    kind: str,
    record_id: str,
    *,
    source: str = SOURCE,
    version: str | None = "1",
) -> ExternalRecordReference:
    return ExternalRecordReference(
        source_system=source,
        record_kind=kind,
        record_id=record_id,
        record_version=version,
    )


def _context() -> DrillingNPTContextEvidence:
    return DrillingNPTContextEvidence(
        context_id=CONTEXT_ID,
        context_reference=_ref("drilling-npt-context", CONTEXT_ID),
        rig_id="RIG-1",
        rig_name="Rig 1",
        rig_reference=_ref("operating-rig", "RIG-SRC-1"),
        well_id="WELL-1",
        well_name="Well 1",
        well_reference=_ref("well", "WELL-SRC-1"),
        activities=[
            DrillingNPTActivityEvidence(
                activity_id="ACT-NPT",
                activity_name="Top drive downtime",
                start_time="2026-10-18T10:00:00+03:00",
                end_time="2026-10-18T12:00:00+03:00",
                classification_id="CLASS-NPT",
                classification_name="Non-productive",
                is_productive=False,
                activity_reference=_ref("drilling-activity-interval", "ACT-SRC-NPT"),
                classification_reference=_ref(
                    "drilling-activity-classification",
                    "CLASS-SRC-NPT",
                ),
            )
        ],
    )


class ProjectionBinding:
    manifest = SyntheticDrillingNPTBinding.manifest

    def __init__(
        self,
        context: DrillingNPTContextEvidence,
        *,
        envelope_reference: ExternalRecordReference | None = None,
    ) -> None:
        self.context = context
        self.envelope_reference = envelope_reference or _ref(
            "drilling-npt-context",
            CONTEXT_ID,
        )

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        return EvidenceEnvelope(
            reference=self.envelope_reference,
            evidence=self.context.model_dump(mode="json"),
        )


class FakeFabricReader:
    def __init__(self, tables: dict[str, list[dict[str, object]]]) -> None:
        self.tables = tables

    def read_rows(self, table_name: str, *, context_id: str) -> list[dict[str, object]]:
        return [
            dict(row)
            for row in self.tables.get(table_name, [])
            if row.get("context_id") == context_id
        ]


def _fabric_tables() -> dict[str, list[dict[str, object]]]:
    return {
        "cepio_drilling_npt_context": [
            {
                "context_id": CONTEXT_ID,
                "source_record_id": CONTEXT_ID,
                "source_record_version": "7",
                "rig_id": "RIG-1",
                "rig_name": "Rig 1",
                "rig_source_record_id": "FAB-RIG-1",
                "rig_source_record_version": "14",
                "well_id": "WELL-1",
                "well_name": "Well 1",
                "well_source_record_id": "FAB-WELL-1",
                "well_source_record_version": "9",
            }
        ],
        "cepio_drilling_activity_interval": [
            {
                "context_id": CONTEXT_ID,
                "activity_id": "ACT-NPT",
                "activity_name": "Top drive downtime",
                "start_time": "2026-10-18T10:00:00+03:00",
                "end_time": "2026-10-18T12:00:00+03:00",
                "source_record_id": "FAB-ACT-NPT",
                "source_record_version": "21",
            }
        ],
        "cepio_drilling_activity_classification": [
            {
                "context_id": CONTEXT_ID,
                "activity_id": "ACT-NPT",
                "classification_id": "CLASS-NPT",
                "classification_name": "Non-productive",
                "is_productive": False,
                "source_record_id": "FAB-CLASS-NPT",
                "source_record_version": "31",
            }
        ],
    }


def _fabric_binding(tables: dict[str, list[dict[str, object]]]) -> FabricDrillingNPTBinding:
    return FabricDrillingNPTBinding(FakeFabricReader(tables))


def test_synthetic_binding_rejects_unknown_and_key_mismatched_contexts():
    binding = SyntheticDrillingNPTBinding({CONTEXT_ID: _context()})
    with pytest.raises(KeyError, match="Unknown synthetic drilling NPT context"):
        binding.resolve_evidence("UNKNOWN-CONTEXT")

    mismatched = _context().model_copy(update={"context_id": "OTHER-CONTEXT"})
    with pytest.raises(ValueError, match="key does not match context_id"):
        SyntheticDrillingNPTBinding({CONTEXT_ID: mismatched}).resolve_evidence(CONTEXT_ID)


def test_domain_projection_rejects_context_identity_and_envelope_reference_drift():
    mismatched = _context().model_copy(update={"context_id": "OTHER-CONTEXT"})
    with pytest.raises(ValueError, match="context identity changed"):
        qualify_drilling_npt_binding(ProjectionBinding(mismatched), external_id=CONTEXT_ID)

    context = _context().model_copy(
        update={
            "context_reference": _ref(
                "drilling-npt-context",
                CONTEXT_ID,
                version="2",
            )
        }
    )
    with pytest.raises(ValueError, match="Envelope reference does not match"):
        qualify_drilling_npt_binding(ProjectionBinding(context), external_id=CONTEXT_ID)


def test_domain_projection_rejects_nested_source_and_version_provenance_gaps():
    context = _context().model_copy(
        update={
            "rig_reference": _ref(
                "operating-rig",
                "RIG-SRC-1",
                source="wrong-source",
            )
        }
    )
    with pytest.raises(ValueError, match="source_system does not match"):
        qualify_drilling_npt_binding(ProjectionBinding(context), external_id=CONTEXT_ID)

    context = _context().model_copy(
        update={
            "rig_reference": _ref(
                "operating-rig",
                "RIG-SRC-1",
                version=None,
            )
        }
    )
    with pytest.raises(ValueError, match="has no record_version"):
        qualify_drilling_npt_binding(ProjectionBinding(context), external_id=CONTEXT_ID)


def test_fabric_binding_rejects_missing_source_identity_and_context_identity_drift():
    tables = _fabric_tables()
    tables["cepio_drilling_npt_context"][0]["source_record_id"] = ""
    with pytest.raises(ValueError, match="missing source_record_id"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)

    tables = _fabric_tables()
    tables["cepio_drilling_npt_context"][0]["source_record_id"] = "OTHER-CONTEXT"
    with pytest.raises(ValueError, match="must equal the requested context_id"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)


def test_fabric_binding_rejects_empty_activity_and_orphan_classification_sets():
    tables = _fabric_tables()
    tables["cepio_drilling_activity_interval"] = []
    with pytest.raises(ValueError, match="contains no activity rows"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)

    tables = _fabric_tables()
    tables["cepio_drilling_activity_classification"].append(
        {
            "context_id": CONTEXT_ID,
            "activity_id": "ACT-ORPHAN",
            "classification_id": "CLASS-ORPHAN",
            "classification_name": "Orphan",
            "is_productive": False,
            "source_record_id": "FAB-CLASS-ORPHAN",
            "source_record_version": "32",
        }
    )
    with pytest.raises(ValueError, match="orphan classifications"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)


def test_fabric_binding_rejects_activity_without_identity_and_missing_rig_or_well():
    tables = _fabric_tables()
    tables["cepio_drilling_activity_interval"][0]["activity_id"] = None
    tables["cepio_drilling_activity_classification"] = []
    with pytest.raises(ValueError, match="row is missing activity_id"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)

    tables = _fabric_tables()
    tables["cepio_drilling_npt_context"][0]["rig_id"] = ""
    with pytest.raises(ValueError, match="must resolve rig_id and well_id"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)
