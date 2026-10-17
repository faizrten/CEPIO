from pathlib import Path

import pytest
from pydantic import ValidationError

from cepio.cross_customer_qualification import (
    CustomerQualificationProfile,
    run_cross_customer_qualification,
)


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "generalization/customers/drilling-contractor-cross-customer-v0.5.yaml"


def test_four_customer_cross_customer_qualification_is_60_of_60_without_semantic_extensions():
    report = run_cross_customer_qualification(ROOT, PACK)

    assert report["cross_customer_qualification_version"] == "0.5"
    assert report["mode"] == "deterministic-cross-customer-runtime-qualification"
    assert report["customer_count"] == 4
    assert report["question_count_per_customer"] == 15
    assert report["total_question_executions"] == 60
    assert report["total_passed_question_executions"] == 60
    assert report["cross_customer_runtime_coverage_rate"] == pytest.approx(1.0)
    assert report["semantic_extension_count"] == 0
    assert report["passed_customers"] == 4
    assert report["status"] == "PASS"

    customers = {customer["customer_id"]: customer for customer in report["customers"]}
    assert set(customers) == {"aro", "sanad", "nabors", "arabian-drilling"}
    assert all(customer["status"] == "PASS" for customer in customers.values())
    assert all(customer["status_counts"] == {"PASS": 15, "FAIL": 0, "ERROR": 0} for customer in customers.values())
    assert all(customer["no_semantic_extension"] for customer in customers.values())
    assert all(customer["operator_evidence_gate_pass"] for customer in customers.values())
    assert {
        customer["semantic_signature_hash"] for customer in customers.values()
    } == {report["canonical_semantic_signature_hash"]}


def test_cross_customer_pack_materially_varies_required_operating_model_dimensions():
    report = run_cross_customer_qualification(ROOT, PACK)

    required = {
        "fleet_scope",
        "ownership_model",
        "market_scope",
        "technology_posture",
        "customer_model",
    }
    assert set(report["required_stress_dimensions"]) == required
    for dimension in required:
        assert len(report["stress_dimension_values"][dimension]) >= 2

    customers = {customer["customer_id"]: customer for customer in report["customers"]}
    assert customers["aro"]["context"]["fleet_scope"] == "offshore-jack-up"
    assert customers["sanad"]["context"]["fleet_scope"] == "onshore-land"
    assert customers["nabors"]["context"]["market_scope"] == "multi-country"
    assert customers["arabian-drilling"]["context"]["fleet_scope"] == "mixed-land-offshore"


def test_customer_profile_cannot_smuggle_canonical_semantic_overrides():
    with pytest.raises(ValidationError):
        CustomerQualificationProfile.model_validate(
            {
                "id": "unsafe-profile",
                "name": "Unsafe Profile",
                "context": {
                    "fleet_scope": "land",
                    "ownership_model": "listed",
                    "market_scope": "single-country",
                    "technology_posture": "standard",
                    "customer_model": "multi-customer",
                },
                "scenario_theme": "Attempted ontology fork",
                "source_evidence": [],
                "semantic_overrides": {
                    "https://cepio.org/ontology/drilling#OperatingRig": "customer:Rig"
                },
            }
        )


def test_profiled_runtime_evidence_remains_customer_scoped_and_fail_closed():
    report = run_cross_customer_qualification(ROOT, PACK)
    sanad = next(customer for customer in report["customers"] if customer["customer_id"] == "sanad")
    first = sanad["results"][0]

    assert first["question_id"] == "DC-DQ-001"
    assert first["operator_evidence_gate"]["passed"] is True
    records = first["evidence_bundle"]["records"]
    object_records = [record for record in records if record["kind"] == "object_snapshot"]
    assert object_records
    assert all(record["payload"]["id"].startswith("SANAD:") for record in object_records)
    assert all(
        record["payload"]["properties"]["qualification:customer_profile"] == "sanad"
        for record in object_records
    )
