from pathlib import Path

import yaml


ARCHETYPE_PATH = Path("generalization/archetypes/drilling-operator-v0.1.yaml")
SCENARIO_PATH = Path("generalization/industry-iq/drilling-operator-scenarios-v0.1.yaml")


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_operator_archetype_preserves_operator_contractor_accountability_boundary():
    payload = _load(ARCHETYPE_PATH)
    boundary = payload["accountability_boundary"]

    assert payload["domain"] == "drilling-operator"
    assert payload["status"] == "frozen"
    assert "approved operational plan and operator change control" in boundary["operator_owns"]
    assert "rig and drilling equipment readiness" in boundary["drilling_contractor_owns"]
    assert "well" in boundary["shared_interface"]
    assert "drilling activity" in boundary["shared_interface"]
    assert payload["principles"]["operator_specific_ontology_fork"] == "prohibited"
    assert payload["principles"]["customer_data_used_for_training"] is False


def test_operator_industry_iq_portfolio_is_frozen_unique_and_complete():
    payload = _load(SCENARIO_PATH)
    scenarios = payload["scenarios"]

    assert payload["version"] == "0.1"
    assert payload["domain"] == "drilling-operator"
    assert payload["frozen"] is True
    assert len(scenarios) == 16
    ids = [item["id"] for item in scenarios]
    assert ids == [f"OP-IQ-{index:03d}" for index in range(1, 17)]
    assert len(ids) == len(set(ids))


def test_only_well_delivery_is_newly_executable_operator_iq():
    scenarios = _load(SCENARIO_PATH)["scenarios"]
    by_id = {item["id"]: item for item in scenarios}

    assert by_id["OP-IQ-001"]["status"] == "executable-v0.1"
    assert by_id["OP-IQ-001"]["pack_id"] == "cepio.iq.drilling.operator-well-delivery"
    assert by_id["OP-IQ-003"]["reuses_pack"] == "cepio.iq.drilling.npt"
    assert all(item["status"] == "planned" for item in scenarios if item["id"] != "OP-IQ-001")


def test_operator_iq_rules_keep_shared_semantics_and_human_authority():
    rules = _load(SCENARIO_PATH)["rules"]

    assert rules["canonical_ontology_changes_for_scenario_pass"] == "prohibited"
    assert rules["operator_specific_ontology_fork"] == "prohibited"
    assert rules["contractor_and_service_evidence_may_inform_operator_iq"] is True
    assert rules["operator_decision_rights_remain_operator_owned"] is True
    assert rules["source_systems_remain_authoritative"] is True
    assert rules["evidence_bindings_are_replaceable"] is True
    assert rules["ai_assessment_is_enterprise_fact"] is False
    assert rules["customer_data_used_for_training"] is False
    assert rules["safety_critical_physical_autonomy"] == "prohibited"
