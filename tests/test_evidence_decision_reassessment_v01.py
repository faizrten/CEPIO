"""Cross-domain regression over existing deterministic CEPIO runtime suites.

This tests evidence graph answerability and negative controls, NOT field qualification,
agent uplift, data freshness, or independently verified human authority.
"""
from pathlib import Path

import pytest
import yaml

from cepio.runtime_coverage import load_runtime_coverage_suite, run_runtime_question


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/regression/evidence-decision-reassessment-v0.1.yaml"
GATE_NAMES = ("evidence", "consequence", "governance_context")


def _manifest():
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    return manifest


def _case(instance, gate):
    suite = load_runtime_coverage_suite(ROOT / instance["runtime_suite"])
    matches = [question for question in suite.questions if question.question_id == gate["question_id"]]
    assert len(matches) == 1, f"missing/ambiguous question: {instance['id']} {gate['question_id']}"
    return suite, matches[0]


def test_cross_domain_manifest_preserves_north_star_boundaries():
    manifest = _manifest()
    assert manifest["pattern"] == "evidence-change-requires-governed-reassessment"
    assert manifest["qualification"]["field_qualified"] is False
    assert manifest["qualification"]["matched_model_industry_iq_uplift"] == "not_measured"
    assert manifest["qualification"]["live_source_qualification"] == "not_run"
    assert manifest["rules"]["use_existing_runtime_coverage"] is True
    assert manifest["rules"]["provider_neutral"] is True
    assert manifest["rules"]["no_customer_data"] is True
    assert manifest["rules"]["authority_is_not_inferred_from_recommendation"] is True
    instances = manifest["instances"]
    assert len(instances) == 2
    assert len({item["domain"] for item in instances}) == 2
    assert len({item["id"] for item in instances}) == len(instances)
    assert all(item["decision_posture"] == "human-review-required" for item in instances)


@pytest.mark.parametrize("instance_index", (0, 1))
def test_each_domain_reuses_existing_runtime_probes_with_evidence_gate(instance_index):
    instance = _manifest()["instances"][instance_index]
    suite_paths = set()
    for gate_name in GATE_NAMES:
        gate = instance[gate_name]
        suite, case = _case(instance, gate)
        suite_paths.add(suite.competency_pack)
        probe_ids = {probe.id for probe in case.probes}
        required = set(gate["required_probes"])
        assert required and required <= probe_ids
        result = run_runtime_question(case, suite.id, ROOT)
        assert result["status"] == "PASS"
        resolved = {probe["id"]: probe for probe in result["probe_results"]}
        assert all(resolved[probe_id]["status"] == "PASS" for probe_id in required)
        assert result["operator_evidence_gate"] == {
            "supported": "ANSWERED",
            "unsupported": "REJECTED_UNSUPPORTED_EVIDENCE",
            "passed": True,
        }
    assert len(suite_paths) == 1, "one domain instance must use one frozen competency pack"


@pytest.mark.parametrize("instance_index", (0, 1))
@pytest.mark.parametrize("gate_name", ("evidence", "consequence"))
def test_removal_of_required_evidence_link_fails_closed(instance_index, gate_name):
    instance = _manifest()["instances"][instance_index]
    gate = instance[gate_name]
    suite, case = _case(instance, gate)
    case = case.model_copy(deep=True)
    remove_id = gate["remove_relationship_for_negative_test"]
    matching = [edge for edge in case.relationships if edge.id == remove_id]
    assert len(matching) == 1, "negative control must remove a real existing edge"
    case.relationships = [edge for edge in case.relationships if edge.id != remove_id]
    result = run_runtime_question(case, suite.id, ROOT)
    assert result["status"] == "FAIL", "missing evidence must not be accepted"
    assert any(probe["status"] == "FAIL" for probe in result["probe_results"])


def test_no_test_case_claims_that_graph_coverage_is_an_operational_decision():
    manifest = _manifest()
    for instance in manifest["instances"]:
        assert instance["decision_posture"] == "human-review-required"
        for gate_name in GATE_NAMES:
            gate = instance[gate_name]
            _, case = _case(instance, gate)
            assert all(probe.id for probe in case.probes)
    # A relationship to a decision or an authority assignment does not itself
    # prove human approval, a live decision, or a verified source-system action.
    assert manifest["qualification"]["external_action_qualification"] == "not_run"
