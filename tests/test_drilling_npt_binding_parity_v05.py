from __future__ import annotations

import json

import pytest

from cepio.domain_bindings import ExternalRecordReference
from cepio.drilling_npt_binding import (
    DrillingNPTActivityEvidence,
    DrillingNPTContextEvidence,
    qualify_drilling_npt_binding,
)
from cepio.integrations.microsoft.drilling_npt_fabric import FabricDrillingNPTBinding
from cepio.integrations.synthetic.drilling_npt import SyntheticDrillingNPTBinding
from cepio.platform_bindings import qualify_evidence_binding


CONTEXT_ID = "NPT-CONTEXT-001"


def _ref(source: str, kind: str, record_id: str, version: str = "1") -> ExternalRecordReference:
    return ExternalRecordReference(
        source_system=source,
        record_kind=kind,
        record_id=record_id,
        record_version=version,
    )


def _synthetic_binding() -> SyntheticDrillingNPTBinding:
    source = "synthetic-drilling"
    context = DrillingNPTContextEvidence(
        context_id=CONTEXT_ID,
        context_reference=_ref(source, "drilling-npt-context", CONTEXT_ID),
        rig_id="RIG-1",
        rig_name="Rig 1",
        rig_reference=_ref(source, "operating-rig", "RIG-SRC-1"),
        well_id="WELL-1",
        well_name="Well 1",
        well_reference=_ref(source, "well", "WELL-SRC-1"),
        activities=[
            DrillingNPTActivityEvidence(
                activity_id="ACT-NPT",
                activity_name="Top drive downtime",
                start_time="2026-10-18T10:00:00+03:00",
                end_time="2026-10-18T12:00:00+03:00",
                classification_id="CLASS-NPT",
                classification_name="Non-productive",
                is_productive=False,
                activity_reference=_ref(source, "drilling-activity-interval", "ACT-SRC-NPT"),
                classification_reference=_ref(
                    source,
                    "drilling-activity-classification",
                    "CLASS-SRC-NPT",
                ),
            ),
            DrillingNPTActivityEvidence(
                activity_id="ACT-PROD",
                activity_name="Drilling ahead",
                start_time="2026-10-18T12:00:00+03:00",
                end_time="2026-10-18T13:30:00+03:00",
                classification_id="CLASS-PROD",
                classification_name="Productive",
                is_productive=True,
                activity_reference=_ref(source, "drilling-activity-interval", "ACT-SRC-PROD"),
                classification_reference=_ref(
                    source,
                    "drilling-activity-classification",
                    "CLASS-SRC-PROD",
                ),
            ),
        ],
    )
    return SyntheticDrillingNPTBinding({CONTEXT_ID: context})


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
                "raw_payload": {"must": "not cross the binding"},
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
                "raw_payload": "bulk telemetry should remain in Fabric",
            },
            {
                "context_id": CONTEXT_ID,
                "activity_id": "ACT-PROD",
                "activity_name": "Drilling ahead",
                "start_time": "2026-10-18T12:00:00+03:00",
                "end_time": "2026-10-18T13:30:00+03:00",
                "source_record_id": "FAB-ACT-PROD",
                "source_record_version": "22",
            },
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
            },
            {
                "context_id": CONTEXT_ID,
                "activity_id": "ACT-PROD",
                "classification_id": "CLASS-PROD",
                "classification_name": "Productive",
                "is_productive": True,
                "source_record_id": "FAB-CLASS-PROD",
                "source_record_version": "32",
            },
        ],
    }


def _fabric_binding(tables=None) -> FabricDrillingNPTBinding:
    return FabricDrillingNPTBinding(
        FakeFabricReader(tables or _fabric_tables()),
        dataset_id="synthetic-drilling-connect-v05",
    )


def test_synthetic_and_fabric_bindings_conform_to_same_platform_contract():
    synthetic = qualify_evidence_binding(_synthetic_binding(), external_id=CONTEXT_ID)
    fabric = qualify_evidence_binding(_fabric_binding(), external_id=CONTEXT_ID)

    assert synthetic.versioned is True
    assert fabric.versioned is True
    assert synthetic.binding_id == "cepio.binding.synthetic.drilling-npt"
    assert fabric.binding_id == "cepio.binding.microsoft-fabric.drilling-npt"


def test_same_drilling_industry_iq_is_semantically_equivalent_across_bindings():
    synthetic = qualify_drilling_npt_binding(_synthetic_binding(), external_id=CONTEXT_ID)
    fabric = qualify_drilling_npt_binding(_fabric_binding(), external_id=CONTEXT_ID)

    assert synthetic.assessment == fabric.assessment
    assert synthetic.assessment.total_npt_hours == 2.0
    assert synthetic.assessment.nonproductive_activity_ids == ["ACT-NPT"]
    assert synthetic.semantic_signature == fabric.semantic_signature
    assert synthetic.source_system == "synthetic-drilling"
    assert fabric.source_system == "microsoft-fabric"
    assert {ref.source_system for ref in synthetic.evidence_references} == {"synthetic-drilling"}
    assert {ref.source_system for ref in fabric.evidence_references} == {"microsoft-fabric"}


def test_fabric_binding_keeps_bulk_payload_outside_cepio_evidence_projection():
    envelope = _fabric_binding().resolve_evidence(CONTEXT_ID)
    serialized = json.dumps(envelope.evidence, sort_keys=True)

    assert "raw_payload" not in serialized
    assert "bulk telemetry" not in serialized
    assert envelope.reference.dataset_id == "synthetic-drilling-connect-v05"


def test_evidence_bindings_are_read_only():
    assert not hasattr(_synthetic_binding(), "write_governed")
    assert not hasattr(_fabric_binding(), "write_governed")


def test_fabric_binding_fails_closed_when_context_is_missing_or_duplicated():
    missing = _fabric_binding({
        "cepio_drilling_npt_context": [],
        "cepio_drilling_activity_interval": [],
        "cepio_drilling_activity_classification": [],
    })
    with pytest.raises(KeyError, match="No context row"):
        missing.resolve_evidence(CONTEXT_ID)

    tables = _fabric_tables()
    tables["cepio_drilling_npt_context"].append(dict(tables["cepio_drilling_npt_context"][0]))
    with pytest.raises(ValueError, match="exactly one context row"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)


def test_fabric_binding_fails_closed_on_missing_or_conflicting_classification():
    tables = _fabric_tables()
    tables["cepio_drilling_activity_classification"] = [
        row
        for row in tables["cepio_drilling_activity_classification"]
        if row["activity_id"] != "ACT-NPT"
    ]
    with pytest.raises(ValueError, match="ACT-NPT has no Fabric"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)

    tables = _fabric_tables()
    duplicate = dict(tables["cepio_drilling_activity_classification"][0])
    duplicate["source_record_id"] = "FAB-CLASS-NPT-DUP"
    tables["cepio_drilling_activity_classification"].append(duplicate)
    with pytest.raises(ValueError, match="ACT-NPT has 2 Fabric classifications"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)


def test_fabric_binding_requires_versioned_source_identity():
    tables = _fabric_tables()
    tables["cepio_drilling_activity_interval"][0]["source_record_version"] = None

    with pytest.raises(ValueError, match="missing source_record_version"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)


def test_fabric_binding_rejects_non_boolean_productivity_semantics():
    tables = _fabric_tables()
    tables["cepio_drilling_activity_classification"][0]["is_productive"] = "false"

    with pytest.raises(ValueError, match="is_productive must be boolean"):
        _fabric_binding(tables).resolve_evidence(CONTEXT_ID)
