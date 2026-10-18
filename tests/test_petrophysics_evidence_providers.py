from pathlib import Path

import pytest
import yaml

from cepio.integrations.microsoft.petrophysics_fabric import (
    FabricPetrophysicsEvidenceProvider,
    InMemoryFabricTableReader,
)
from cepio.petrophysics_evidence import (
    EvidenceProviderCapabilityError,
    PetrophysicsOperationalRuntime,
    SyntheticPetrophysicsEvidenceProvider,
)


ROOT = Path(__file__).parents[1]
BINDING = ROOT / "integrations" / "microsoft" / "fabric_iq" / "petrophysics-v1.evidence.yaml"
FABRIC_FIXTURE = (
    ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-v1-fabric-tables.yaml"
)


def _providers():
    synthetic = SyntheticPetrophysicsEvidenceProvider(ROOT)
    reader = InMemoryFabricTableReader.from_yaml(FABRIC_FIXTURE)
    fabric = FabricPetrophysicsEvidenceProvider(reader, BINDING)
    return synthetic, fabric


def test_synthetic_provider_exposes_full_v1_and_fabric_provider_is_bounded():
    synthetic, fabric = _providers()
    assert synthetic.supported_journeys == {
        "PET-01",
        "PET-02",
        "PET-03",
        "PET-04",
        "PET-05",
        "PET-06",
        "PET-07",
        "PET-08",
    }
    assert fabric.supported_journeys == {"PET-02", "PET-05", "PET-06"}

    operational = PetrophysicsOperationalRuntime(fabric, resource_root=ROOT)
    with pytest.raises(EvidenceProviderCapabilityError):
        operational.execute("PET-03")


def test_fabric_binding_is_normalized_and_explicitly_excludes_bulk_curves():
    binding = yaml.safe_load(BINDING.read_text())
    assert binding["source_type"] == "lakehouse"
    assert binding["scope"]["journeys"] == ["PET-02", "PET-05", "PET-06"]
    assert len(set(binding["tables"].values())) == len(binding["tables"])
    assert "do_not_materialize_bulk_log_curves_in_cepio" in binding["invariants"]

    fixture_text = FABRIC_FIXTURE.read_text()
    assert "curve_values" not in fixture_text
    assert "las_payload" not in fixture_text
    assert "bulk_log_payload" not in fixture_text


def test_pet02_has_provider_independent_semantic_output():
    synthetic, fabric = _providers()
    synthetic_runtime = PetrophysicsOperationalRuntime(synthetic, resource_root=ROOT)
    fabric_runtime = PetrophysicsOperationalRuntime(fabric, resource_root=ROOT)

    expected = synthetic_runtime.execute("PET-02", well="A-17", interval="Zone-B")
    actual = fabric_runtime.execute("PET-02", well="A-17", interval="Zone-B")

    assert expected.status == "ANSWERED"
    assert actual.status == "ANSWERED"
    assert expected.answer is not None
    assert actual.answer is not None
    assert actual.answer.model_dump(mode="json") == expected.answer.model_dump(mode="json")
    assert [item.id for item in actual.answer.contradictory_evidence] == ["EV-CORE-RCA"]
    assert {item.id for item in actual.answer.downstream_impact} == {
        "SM18",
        "RM21",
        "RC26",
        "OP-118",
        "DEC-INFILL-R3-2026",
    }


def test_fabric_pet02_preserves_original_source_identity_and_version():
    _, fabric = _providers()
    package = fabric.resolve_pet02(well="A-17", interval="Zone-B")
    evidence = {item["id"]: item for item in package["external_evidence"]}

    assert evidence["EV-GR-RHOB-NPHI"]["source_ref"] == {
        "source_system": "osdu",
        "source_service": "wellbore_ddms",
        "record_kind": "work-product-component--WellLog",
        "record_id": "opendes:work-product-component--WellLog:A17-PETRO-MAIN",
        "record_version": "1759000000000001",
        "partition": "opendes",
    }
    assert evidence["EV-CORE-RCA"]["source_ref"]["record_version"] == "1759000000000003"
    assert evidence["EV-PRESSURE"]["source_ref"]["source_system"] == "customer_profile"


def test_pet05_cross_well_consistency_is_provider_independent():
    synthetic, fabric = _providers()
    synthetic_result = PetrophysicsOperationalRuntime(synthetic, resource_root=ROOT).execute(
        "PET-05"
    )
    fabric_result = PetrophysicsOperationalRuntime(fabric, resource_root=ROOT).execute("PET-05")

    assert synthetic_result.status == "ANSWERED"
    assert fabric_result.status == "ANSWERED"
    assert fabric_result.answer == synthetic_result.answer
    inconsistent = {item["well"] for item in fabric_result.answer["inconsistent_wells"]}
    assert inconsistent == {"A-14", "A-22"}


def test_pet06_model_handover_is_provider_independent():
    synthetic, fabric = _providers()
    synthetic_result = PetrophysicsOperationalRuntime(synthetic, resource_root=ROOT).execute(
        "PET-06"
    )
    fabric_result = PetrophysicsOperationalRuntime(fabric, resource_root=ROOT).execute("PET-06")

    assert synthetic_result.status == "ANSWERED"
    assert fabric_result.status == "ANSWERED"
    assert fabric_result.answer == synthetic_result.answer
    assert fabric_result.answer["source_case"] == "FE-A17-ZB-v3"
    assert fabric_result.answer["downstream_chain"] == ["SM18", "RM21", "FCST-RM21-2026"]
    assert fabric_result.answer["stale_dependencies"] == [
        {
            "well": "A-14",
            "source_case": "FE-A14-ZB-v5",
            "current_transform": "K_TRANSFORM_V5",
            "consumed_transform": "K_TRANSFORM_V4",
            "consumer": "SM18",
        }
    ]


def test_fabric_provider_fails_closed_when_required_context_is_missing():
    binding = yaml.safe_load(BINDING.read_text())
    reader = InMemoryFabricTableReader({name: [] for name in binding["tables"].values()})
    provider = FabricPetrophysicsEvidenceProvider(reader, binding)
    with pytest.raises(EvidenceProviderCapabilityError):
        provider.resolve_pet02(well="A-17", interval="Zone-B")
