from pathlib import Path

import yaml


SCENARIO_PATH = Path("generalization/industry-iq/drilling-contractor-scenarios-v0.6.yaml")


def _load():
    return yaml.safe_load(SCENARIO_PATH.read_text(encoding="utf-8"))


def test_drilling_industry_iq_portfolio_is_frozen_and_unique():
    payload = _load()
    scenarios = payload["scenarios"]

    assert payload["version"] == "0.6"
    assert payload["domain"] == "drilling-contractor"
    assert len(scenarios) == 16
    ids = [item["id"] for item in scenarios]
    assert len(ids) == len(set(ids))
    assert ids == [f"DR-IQ-{index:03d}" for index in range(1, 17)]


def test_only_implemented_drilling_iq_packs_are_marked_executable():
    payload = _load()
    by_id = {item["id"]: item for item in payload["scenarios"]}

    assert by_id["DR-IQ-001"]["pack_id"] == "cepio.iq.drilling.rig-readiness"
    assert by_id["DR-IQ-001"]["status"] == "executable-v0.1"
    assert by_id["DR-IQ-002"]["pack_id"] == "cepio.iq.drilling.npt"
    assert by_id["DR-IQ-002"]["status"] == "executable-v0.1"
    assert all(
        item["status"] == "planned"
        for item in payload["scenarios"]
        if item["id"] not in {"DR-IQ-001", "DR-IQ-002"}
    )


def test_scenario_rules_preserve_new_north_star_boundaries():
    rules = _load()["rules"]

    assert rules["canonical_ontology_changes_for_scenario_pass"] == "prohibited"
    assert rules["readiness_is_derived"] is True
    assert rules["customer_data_used_for_training"] is False
    assert rules["source_systems_remain_authoritative"] is True
    assert rules["evidence_bindings_are_replaceable"] is True
    assert rules["safety_critical_physical_autonomy"] == "prohibited"
