from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
MAPPING = ROOT / "mappings" / "osdu_subsurface_bindings.yaml"


def _contract() -> dict:
    return yaml.safe_load(MAPPING.read_text())


def test_osdu_subsurface_contract_has_expected_boundary_model():
    contract = _contract()
    assert contract["schema_version"] == "0.1"
    assert contract["baseline"]["osdu_milestone"] == "M26"
    assert contract["baseline"]["adme_alignment"] == "M26"
    assert contract["principles"]["treatments"] == ["REUSE", "BIND", "EXTEND", "OWN"]


def test_bound_and_extended_objects_do_not_duplicate_osdu_payloads():
    contract = _contract()
    allowed = {"REUSE", "BIND", "EXTEND"}
    forbidden_storage = {
        "canonical_payload_copy",
        "bulk_payload_copy",
        "cepio_authoritative_copy",
    }

    for item in contract["objects"]:
        assert item["treatment"] in allowed
        assert item["storage_policy"] not in forbidden_storage
        if item["treatment"] == "BIND":
            assert item.get("cepio_type")
            assert item["storage_policy"] == "identity_operating_context_only"
        if item["treatment"] == "EXTEND":
            assert item["storage_policy"] == "external_reference_plus_cepio_sidecar"
            assert item.get("sidecar_semantics")
        if item["treatment"] == "REUSE":
            assert item["storage_policy"] == "external_reference_only"


def test_cepio_owned_subsurface_reasoning_uses_core_epistemic_types():
    contract = _contract()
    expected = {
        "https://cepio.org/ontology/core#Evidence",
        "https://cepio.org/ontology/core#Hypothesis",
        "https://cepio.org/ontology/core#Assumption",
        "https://cepio.org/ontology/core#UncertaintyAssessment",
        "https://cepio.org/ontology/core#ConfidenceAssessment",
        "https://cepio.org/ontology/core#InformationGain",
    }
    actual = {item["type"] for item in contract["cepio_native"]}
    assert actual == expected
    assert all(item["treatment"] == "OWN" for item in contract["cepio_native"])


def test_current_adme_gaps_are_capability_gaps_not_cepio_reimplementations():
    contract = _contract()
    unavailable = set(contract["providers"]["adme"]["unavailable_or_not_primary"])
    assert "production_ddms" in unavailable
    assert "well_delivery_ddms" in unavailable

    production = contract["runtime_capabilities"]["subsurface.production.timeseries"]
    assert production["preferred_binding"] is None
    assert production["fallback_strategy"] == "customer_profile_binding"


def test_acz_partial_support_is_explicit():
    acz = _contract()["providers"]["adme"]["analytics_consumption_zone"]
    assert acz["status"] == "preview_partial"
    unsupported = set(acz["unsupported_scope"])
    assert {"reservoir_ddms", "seismic_ddms", "rock_fluid_samples_ddms"} <= unsupported


def test_anti_duplication_invariants_cover_bulk_and_identity():
    invariants = set(_contract()["anti_duplication_invariants"])
    assert "cepio_must_not_store_seismic_bulk_payload" in invariants
    assert "cepio_must_not_store_well_log_bulk_payload" in invariants
    assert "cepio_must_not_store_resqml_bulk_payload" in invariants
    assert "cepio_must_preserve_osdu_record_and_version_identity" in invariants
    assert "cepio_must_not_assume_acz_supports_all_subsurface_ddms" in invariants
