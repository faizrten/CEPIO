from pathlib import Path

import yaml
from rdflib import Graph, Namespace, OWL, RDF, RDFS

from cepio.petrophysics_v1 import PetrophysicsV1Runtime

ROOT = Path(__file__).parents[1]
BENCHMARK = ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-v1-portfolio.yaml"
PERSONA = ROOT / "generalization" / "personas" / "subsurface-petrophysics-v1.yaml"
CONTRACT = ROOT / "generalization" / "competency" / "subsurface-petrophysics-v1-persona-coverage.yaml"

SUB = Namespace("https://cepio.org/ontology/subsurface#")
CORE = Namespace("https://cepio.org/ontology/core#")


def runtime() -> PetrophysicsV1Runtime:
    return PetrophysicsV1Runtime.from_yaml(BENCHMARK)


def test_v1_persona_declares_complete_petrophysics_journey_set():
    persona = yaml.safe_load(PERSONA.read_text())
    ids = [j["id"] for j in persona["journeys"]]
    assert ids == ["PET-01", "PET-02", "PET-03", "PET-04", "PET-05", "PET-06", "PET-07", "PET-08"]
    assert persona["milestone"] == "CEPIO Petrophysics v1 Persona Coverage"


def test_v1_benchmark_is_explicitly_synthetic_and_not_field_calibrated():
    benchmark = yaml.safe_load(BENCHMARK.read_text())
    assert benchmark["synthetic"] is True
    assert benchmark["provenance"]["source_dataset"] == "none"
    assert benchmark["provenance"]["fictional_identifiers"] is True
    assert any("not calibrated" in item for item in benchmark["provenance"]["limitations"])


def test_subsurface_v1_uses_thin_assurance_semantics():
    graph = Graph()
    graph.parse(ROOT / "ontologies" / "subsurface.ttl", format="turtle")
    expected = [
        SUB.PetrophysicsAssuranceCase,
        SUB.DataReadinessAssessment,
        SUB.SaturationContactAssessment,
        SUB.InterpretationConsistencyAssessment,
        SUB.ModelHandoverTrace,
        SUB.RemainingHydrocarbonAssessment,
        SUB.NewWellLearningAssessment,
    ]
    for concept in expected:
        assert (concept, RDF.type, OWL.Class) in graph
    assert (SUB.FormationEvaluationCase, RDFS.subClassOf, SUB.PetrophysicsAssuranceCase) in graph
    for assessment in (
        SUB.DataReadinessAssessment,
        SUB.SaturationContactAssessment,
        SUB.InterpretationConsistencyAssessment,
        SUB.RemainingHydrocarbonAssessment,
        SUB.NewWellLearningAssessment,
    ):
        assert (assessment, RDFS.subClassOf, CORE.Assessment) in graph


def test_all_petrophysics_v1_journeys_execute_green():
    result = runtime().execute_all()
    assert result.complete is True
    assert result.passed == 8
    assert result.blocked == 0
    assert all(item.status == "ANSWERED" for item in result.results.values())


def test_all_new_v1_skill_preflights_are_ready_for_petrophysicist():
    r = runtime()
    for journey_id in ["PET-01", "PET-03", "PET-04", "PET-05", "PET-06", "PET-07", "PET-08"]:
        result = r.execute(journey_id)
        assert result.status == "ANSWERED"
        assert result.preflights
        assert all(item.status == "READY" for item in result.preflights)


def test_pet01_exposes_data_readiness_without_inventing_missing_evidence():
    answer = runtime().execute("PET-01").answer
    assert answer is not None
    assert answer["best_ready_context"] == "A-17"
    assert answer["readiness_by_well"]["A-17"]["ready_for_full_v1"] is True
    assert "routine_core_analysis" in answer["readiness_by_well"]["A-11"]["missing"]
    assert "downstream_model_identity" in answer["readiness_by_well"]["A-22"]["missing"]


def test_pet03_surfaces_contact_and_saturation_outlier():
    answer = runtime().execute("PET-03").answer
    assert answer is not None
    assert answer["consensus_contact_tvdss_m"] == -2422
    outliers = {item["well"]: item for item in answer["outlier_wells"]}
    assert "A-22" in outliers
    assert "methodology" in outliers["A-22"]["reasons"]
    assert "RC26" in answer["downstream_sensitivity"]
    assert "DEC-INFILL-R3-2026" in answer["downstream_sensitivity"]


def test_pet04_preserves_core_log_contradiction_and_challenges_transform():
    answer = runtime().execute("PET-04").answer
    assert answer is not None
    contradictory = {item["rock_type"]: item for item in answer["contradictory_rock_types"]}
    reconciled = {item["rock_type"]: item for item in answer["reconciled_rock_types"]}
    assert "RT-3" in contradictory
    assert contradictory["RT-3"]["core_permeability_md"] == 71
    assert contradictory["RT-3"]["log_permeability_md"] == 112
    assert "RT-2" in reconciled
    assert "K_TRANSFORM_V5" in answer["challenged_transforms"]


def test_pet05_detects_cross_well_interpretation_drift():
    answer = runtime().execute("PET-05").answer
    assert answer is not None
    by_well = {item["well"]: item for item in answer["inconsistent_wells"]}
    assert "A-22" in by_well
    a22_fields = {d["field"] for d in by_well["A-22"]["deviations"]}
    assert {"method", "rw_ohm_m", "porosity_cutoff_fraction", "sw_cutoff_fraction", "permeability_transform"} <= a22_fields
    assert "A-14" in by_well
    assert any(d["field"] == "permeability_transform" for d in by_well["A-14"]["deviations"])


def test_pet06_traces_model_handover_and_stale_dependency():
    answer = runtime().execute("PET-06").answer
    assert answer is not None
    assert answer["source_case"] == "FE-A17-ZB-v3"
    assert answer["downstream_chain"][:2] == ["SM18", "RM21"]
    phie = next(item for item in answer["transformations"] if item["id"] == "UPSCALE-PHIE-SM18")
    assert phie["from"] == 0.178
    assert phie["to"] == 0.163
    assert phie["changed"] is True
    assert answer["stale_dependencies"][0]["well"] == "A-14"
    assert answer["stale_dependencies"][0]["consumed_transform"] == "K_TRANSFORM_V4"


def test_pet07_links_petrophysics_to_opportunity_without_deciding():
    answer = runtime().execute("PET-07").answer
    assert answer is not None
    assert answer["remaining_hydrocarbon_assessment"]["id"] == "RHA-R3-ZC-2026"
    assert answer["opportunity"]["id"] == "OP-R3-ZC-REMAINING"
    assert len(answer["opportunity"]["options"]) == 4
    assert answer["recommendation"]["option"] == "OPT-DEFER"
    assert answer["recommendation"]["authority"] == "recommend_only"


def test_pet08_computes_prior_posterior_learning_and_information_gain():
    answer = runtime().execute("PET-08").answer
    assert answer is not None
    assert answer["belief_delta"]["phie_fraction"]["delta"] == 0.018
    assert answer["belief_delta"]["sw_fraction"]["delta"] == -0.07
    assert answer["belief_delta"]["net_pay_m"]["delta"] == 3.3
    assert answer["belief_delta"]["contact_tvdss_m"]["delta"] == -5
    assert "fluid_contact" in answer["information_gain"]["uncertainty_reduced"]
    assert "RC26" in answer["downstream_updates"]
    assert "OP-118" in answer["downstream_updates"]


def test_non_petrophysics_actor_fails_closed():
    result = runtime().execute("PET-03", actor_id="operator", actor_roles={"operator"})
    assert result.status == "BLOCKED"
    assert result.blockers
    assert result.blockers[0].code == "SKILL_PREFLIGHT_BLOCKED"


def test_v1_contract_requires_all_eight_journeys():
    contract = yaml.safe_load(CONTRACT.read_text())
    assert contract["coverage_gate"]["required_answered"] == 8
    assert contract["coverage_gate"]["required_blocked"] == 0
    assert contract["scope"]["journeys"] == ["PET-01", "PET-02", "PET-03", "PET-04", "PET-05", "PET-06", "PET-07", "PET-08"]
