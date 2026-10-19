from __future__ import annotations

from pathlib import Path

import pytest

from cepio.integrations.microsoft.fabric_live_proof import (
    FabricLiveProofError,
    load_reference_context,
    run_fabric_drilling_npt_live_proof,
)


REFERENCE = Path("examples/fabric/drilling-npt/reference-context.json")


class DictReader:
    def __init__(self, *, productive_override: bool | None = None) -> None:
        self.productive_override = productive_override

    def read_rows(self, table_name: str, *, context_id: str):
        assert context_id == "NPT-CONTEXT-001"
        if table_name == "cepio_drilling_npt_context":
            return [{
                "context_id": context_id, "source_record_id": context_id,
                "source_record_version": "7", "rig_id": "RIG-1", "rig_name": "Rig 1",
                "rig_source_record_id": "FAB-RIG-1", "rig_source_record_version": "14",
                "well_id": "WELL-1", "well_name": "Well 1",
                "well_source_record_id": "FAB-WELL-1", "well_source_record_version": "9",
            }]
        if table_name == "cepio_drilling_activity_interval":
            return [
                {
                    "context_id": context_id, "activity_id": "ACT-NPT",
                    "activity_name": "Top drive downtime",
                    "start_time": "2026-10-18T10:00:00+03:00",
                    "end_time": "2026-10-18T12:00:00+03:00",
                    "source_record_id": "FAB-ACT-NPT", "source_record_version": "21",
                },
                {
                    "context_id": context_id, "activity_id": "ACT-PROD",
                    "activity_name": "Drilling ahead",
                    "start_time": "2026-10-18T12:00:00+03:00",
                    "end_time": "2026-10-18T13:30:00+03:00",
                    "source_record_id": "FAB-ACT-PROD", "source_record_version": "22",
                },
            ]
        if table_name == "cepio_drilling_activity_classification":
            npt_productive = False if self.productive_override is None else self.productive_override
            return [
                {
                    "context_id": context_id, "activity_id": "ACT-NPT",
                    "classification_id": "CLASS-NPT", "classification_name": "Non-productive",
                    "is_productive": npt_productive,
                    "source_record_id": "FAB-CLASS-NPT", "source_record_version": "31",
                },
                {
                    "context_id": context_id, "activity_id": "ACT-PROD",
                    "classification_id": "CLASS-PROD", "classification_name": "Productive",
                    "is_productive": True,
                    "source_record_id": "FAB-CLASS-PROD", "source_record_version": "32",
                },
            ]
        raise AssertionError(table_name)


def test_live_proof_runs_same_industry_iq_across_synthetic_and_fabric():
    reference = load_reference_context(REFERENCE)
    result = run_fabric_drilling_npt_live_proof(
        DictReader(), reference_context=reference, dataset_id="fabric-live-proof"
    )

    assert result.binding_contract_version == "0.1"
    assert result.binding_id == "cepio.binding.microsoft-fabric.drilling-npt"
    assert result.provider_id == "microsoft-fabric"
    assert result.capability_id == "drilling-npt-context"
    assert result.context_id == "NPT-CONTEXT-001"
    assert result.dataset_id == "fabric-live-proof"
    assert result.total_npt_hours == 2.0
    assert result.nonproductive_activity_ids == ("ACT-NPT",)
    assert result.evidence_reference_count == 7
    assert result.synthetic_source_system == "synthetic-drilling"
    assert result.fabric_source_system == "microsoft-fabric"


def test_live_proof_fails_when_fabric_semantics_drift_from_control():
    reference = load_reference_context(REFERENCE)
    with pytest.raises(FabricLiveProofError, match="not semantically equivalent"):
        run_fabric_drilling_npt_live_proof(
            DictReader(productive_override=True), reference_context=reference
        )
