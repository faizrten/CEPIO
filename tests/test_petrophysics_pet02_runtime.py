from copy import deepcopy
from pathlib import Path

import yaml

from cepio import FormationEvaluationAssuranceRuntime, run_pet02_formation_evaluation


ROOT = Path(__file__).parents[1]
BENCHMARK = (
    ROOT
    / "generalization"
    / "benchmarks"
    / "subsurface-petrophysics-pet02-a17-zone-b.yaml"
)


def _payload() -> dict:
    return yaml.safe_load(BENCHMARK.read_text(encoding="utf-8"))


def test_pet02_runtime_answers_the_golden_question_end_to_end():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-17", interval="Zone-B")

    assert result.status == "ANSWERED"
    assert not result.blockers
    assert len(result.preflights) == 5
    assert all(item.status == "READY" for item in result.preflights)
    assert result.answer is not None
    assert result.answer.authoritative_case == "FE-A17-ZB-v3"
    assert result.answer.authority_state == "Authoritative"
    assert result.answer.superseded_case == "FE-A17-ZB-v2"
    assert result.answer.benchmark_synthetic is True
    assert result.answer.benchmark_origin == "CEPIO-authored synthetic fixture"
    assert result.answer.human_authority_required is True
    assert "declare_authoritative" in result.answer.prohibited_ai_conclusions


def test_pet02_runtime_computes_interpretation_delta_instead_of_copying_expected_answer():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-17", interval="Zone-B")
    answer = result.answer
    assert answer is not None

    changed_assumptions = {item.name: (item.previous, item.current) for item in answer.changed_assumptions}
    assert changed_assumptions["rw_ohm_m"] == (0.071, 0.064)
    assert changed_assumptions["archie_m"] == (2.0, 2.15)
    assert changed_assumptions["porosity_cutoff_fraction"] == (0.10, 0.09)
    assert changed_assumptions["permeability_transform"] == ("K_TRANSFORM_V4", "K_TRANSFORM_V5")

    changed_findings = {item.name: (item.previous, item.current) for item in answer.changed_findings}
    assert changed_findings["water_saturation_fraction"] == (0.34, 0.29)
    assert changed_findings["net_pay_m"] == (11.2, 13.8)
    assert changed_findings["fluid_contact_tvdss_m"] == (-2418, -2423)
    assert changed_findings["permeability_md"] == (88, 112)


def test_pet02_runtime_preserves_external_record_and_version_provenance():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-17", interval="Zone-B")
    answer = result.answer
    assert answer is not None

    evidence = {item.id: item for item in answer.supporting_evidence + answer.contradictory_evidence}
    assert evidence["EV-GR-RHOB-NPHI"].source_ref.source_system == "osdu"
    assert evidence["EV-GR-RHOB-NPHI"].source_ref.source_service == "wellbore_ddms"
    assert evidence["EV-GR-RHOB-NPHI"].source_ref.record_version == "1759000000000001"
    assert evidence["EV-CORE-RCA"].source_ref.source_service == "rock_fluid_samples_ddms"
    assert evidence["EV-CORE-RCA"].source_ref.record_version == "1759000000000003"


def test_pet02_runtime_surfaces_core_log_contradiction_and_qualifies_confidence():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-17", interval="Zone-B")
    answer = result.answer
    assert answer is not None

    assert [item.id for item in answer.contradictory_evidence] == ["EV-CORE-RCA"]
    conflict = answer.contradictory_evidence[0]
    assert conflict.observed_values["observed_permeability_md"] == 71
    assert conflict.comparison_target == "FE-A17-ZB-v3.findings.permeability_md"
    assert answer.current_findings["permeability_md"] == 112
    assert answer.confidence[0].rating == "moderate_high"
    assert "core-log permeability disagreement" in answer.confidence[0].rationale
    assert answer.recommended_actions[0].action_type == "technical_review"
    assert answer.recommended_actions[0].authority == "recommend_only"


def test_pet02_runtime_exposes_uncertainty_and_traces_transitive_downstream_impact():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-17", interval="Zone-B")
    answer = result.answer
    assert answer is not None

    uncertainty = {item.assesses: item for item in answer.uncertainty}
    assert set(uncertainty) == {"water_saturation", "fluid_contact"}
    assert uncertainty["water_saturation"].assessment == {
        "lower_fraction": 0.25,
        "central_fraction": 0.29,
        "upper_fraction": 0.35,
    }

    impact = {item.id: item for item in answer.downstream_impact}
    assert set(impact) == {"SM18", "RM21", "RC26", "OP-118", "DEC-INFILL-R3-2026"}
    assert impact["SM18"].depends_on == ["FE-A17-ZB-v3"]
    assert impact["RM21"].depends_on == ["SM18"]
    assert impact["DEC-INFILL-R3-2026"].depends_on == ["OP-118", "RM21"]
    assert answer.recommended_actions[-1].action_type == "information_gain"


def test_pet02_runtime_emits_the_five_skill_execution_trace():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-17", interval="Zone-B")
    ids = [item.skill_id for item in result.trace]
    assert ids == [
        "cepio.skill.subsurface.petrophysics.formation-evaluation-context",
        "cepio.skill.subsurface.petrophysics.interpretation-delta",
        "cepio.skill.subsurface.petrophysics.assumption-trace",
        "cepio.skill.subsurface.petrophysics.core-log-reconciliation",
        "cepio.skill.subsurface.petrophysics.downstream-impact",
    ]
    assert all(item.status == "PASS" for item in result.trace)


def test_pet02_runtime_fails_closed_when_actor_cannot_pass_skill_preflight():
    result = run_pet02_formation_evaluation(
        BENCHMARK,
        well="A-17",
        interval="Zone-B",
        actor_id="unauthorized-user",
        actor_roles={"shareholder_viewer"},
    )
    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.answer is None
    assert any(item.status == "BLOCKED" for item in result.preflights)
    assert all(blocker.code == "SKILL_PREFLIGHT_BLOCKED" for blocker in result.blockers)


def test_pet02_runtime_fails_closed_when_requested_context_is_absent():
    result = run_pet02_formation_evaluation(BENCHMARK, well="A-99", interval="Zone-B")
    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.answer is None
    assert result.blockers[0].code == "CONTEXT_NOT_FOUND"


def test_pet02_runtime_fails_closed_on_multiple_authoritative_cases():
    payload = _payload()
    mutated = deepcopy(payload)
    mutated["formation_evaluation_cases"][0]["state"] = (
        "https://cepio.org/ontology/subsurface#Authoritative"
    )

    result = FormationEvaluationAssuranceRuntime(mutated).execute(well="A-17", interval="Zone-B")
    assert result.status == "AUTHORITY_CONFLICT"
    assert result.answer is None
    assert result.blockers[0].code == "MULTIPLE_AUTHORITATIVE_CASES"


def test_pet02_runtime_fails_closed_when_external_version_identity_is_missing():
    payload = _payload()
    mutated = deepcopy(payload)
    del mutated["external_evidence"][0]["source_ref"]["record_version"]

    result = FormationEvaluationAssuranceRuntime(mutated).execute(well="A-17", interval="Zone-B")
    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.answer is None
    assert result.blockers[0].code == "SOURCE_VERSION_IDENTITY_INCOMPLETE"
