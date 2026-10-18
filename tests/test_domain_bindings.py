from pathlib import Path

import pytest
from pydantic import ValidationError

from cepio.domain_bindings import (
    DomainBindingContract,
    DomainObjectBinding,
    ExternalRecordReference,
)


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "mappings" / "osdu_subsurface_bindings.yaml"


def test_subsurface_contract_loads_through_runtime_model():
    contract = DomainBindingContract.load_yaml(CONTRACT)
    assert contract.profile == "osdu-adme-subsurface"
    assert contract.baseline["osdu_milestone"] == "M26"
    assert (
        contract.resolve_preferred_binding("subsurface.reservoir.model_scenario")
        == "adme.reservoir_ddms"
    )


def test_object_binding_preserves_treatment_and_provider_service():
    contract = DomainBindingContract.load_yaml(CONTRACT)
    fault = contract.object_binding("fault_interpretation")
    assert fault.treatment == "EXTEND"
    assert fault.provider_service == "reservoir_ddms"
    assert (
        "https://cepio.org/ontology/core#UncertaintyAssessment"
        in fault.sidecar_semantics
    )

    well = contract.object_binding("well")
    assert well.treatment == "BIND"
    assert well.cepio_type == "https://cepio.org/ontology/energy#Well"


def test_external_record_reference_preserves_versioned_external_identity():
    ref = ExternalRecordReference(
        source_system="adme",
        source_service="reservoir_ddms",
        record_kind="work-product-component--ReservoirModelScenario",
        record_id="tenant:work-product-component--ReservoirModelScenario:rm-21",
        record_version=7,
        partition="opendes",
    )
    assert ref.stable_key.endswith(":7")
    assert ref.record_id == "tenant:work-product-component--ReservoirModelScenario:rm-21"

    with pytest.raises(ValidationError):
        ref.record_version = 8


def test_production_capability_can_be_unbound_without_inventing_provider():
    contract = DomainBindingContract.load_yaml(CONTRACT)
    production = contract.capability("subsurface.production.timeseries")
    assert production.preferred_binding is None
    assert production.fallback_strategy == "customer_profile_binding"


def test_binding_validation_rejects_bind_without_cepio_type():
    with pytest.raises(ValidationError):
        DomainObjectBinding(
            id="bad",
            external_kind="master-data--Something",
            provider_capability="example.something",
            treatment="BIND",
            storage_policy="identity_operating_context_only",
        )


def test_binding_validation_rejects_extend_without_sidecar_semantics():
    with pytest.raises(ValidationError):
        DomainObjectBinding(
            id="bad",
            external_kind="work-product-component--Something",
            provider_capability="example.something",
            treatment="EXTEND",
            storage_policy="external_reference_plus_cepio_sidecar",
        )
