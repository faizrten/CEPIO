from copy import deepcopy
from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

from cepio.production_technology import ProductionTechnologistRuntime


ROOT = Path(__file__).parents[1]
ONTOLOGY = ROOT / "ontologies" / "production.ttl"
MODULES = ROOT / "ontology-modules.yaml"
PERSONA = ROOT / "generalization" / "personas" / "production-technologist-v0.1.yaml"
CONTRACT = ROOT / "generalization" / "competency" / "production-technologist-v0.1.yaml"
BENCHMARK = ROOT / "generalization" / "benchmarks" / "production-technologist-p118-v0.1.yaml"

CEPIO = Namespace("https://cepio.org/ontology/core#")
ENERGY = Namespace("https://cepio.org/ontology/energy#")
KIN = Namespace("https://cepio.org/ontology/kinetic#")
PROD = Namespace("https://cepio.org/ontology/production#")


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_production_module_is_registered_as_experimental_domain_module():
    catalogue = _yaml(MODULES)
    assert "production" in catalogue["architecture"]["domain"]
    module = next(item for item in catalogue["modules"] if item["id"] == "production")
    assert module["version"] == "0.1.0"
    assert module["stability"] == "experimental"
    assert {dependency["module"] for dependency in module["depends_on"]} == {"core", "energy", "kinetic"}


def test_production_ontology_is_assurance_semantics_not_source_payload_replication():
    graph = Graph().parse(ONTOLOGY, format="turtle")
    assert (PROD.ProductionAssuranceCase, RDF.type, OWL.Class) in graph
    assert (PROD.ProductionAssuranceCase, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (PROD.WellPerformanceAssessment, RDFS.subClassOf, CEPIO.Assessment) in graph
    assert (PROD.DeliverabilityAssessment, RDFS.subClassOf, PROD.WellPerformanceAssessment) in graph
    assert (PROD.WellOperatingEnvelope, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (PROD.WellOperatingLimit, RDFS.subClassOf, KIN.Constraint) in graph
    assert (PROD.ProductionDeviation, RDFS.subClassOf, CEPIO.Event) in graph
    assert (PROD.assuranceForWell, RDFS.range, ENERGY.Well) in graph
    assert (PROD.hasOperatingLimit, RDFS.range, PROD.WellOperatingLimit) in graph

    serialized = ONTOLOGY.read_text()
    for forbidden in ("WellTest a owl:Class", "NodalModel a owl:Class", "ProductionTimeSeries a owl:Class", "FlowNetwork a owl:Class"):
        assert forbidden not in serialized


def test_persona_freezes_ten_journeys_and_three_executable_depth_anchors():
    persona = _yaml(PERSONA)
    journeys = {item["id"]: item for item in persona["journeys"]}
    assert set(journeys) == {f"PROD-{index:02d}" for index in range(1, 11)}
    assert {journey_id for journey_id, item in journeys.items() if item["executable_v0_1"]} == {"PROD-01", "PROD-02", "PROD-06"}
    authority = next(item for item in persona["persona_family"]["authority_profiles"] if item["id"] == "production_technologist")
    assert "recommend" in authority["may"]
    assert "change_live_setpoint" in authority["must_handoff"]
    assert "override_operating_envelope" in authority["must_handoff"]


def test_competency_contract_preserves_source_boundary_and_runtime_capabilities():
    contract = _yaml(CONTRACT)
    treatments = {item["id"]: item["treatment"] for item in contract["semantic_boundary"]["objects"]}
    assert treatments["well"] == "BIND"
    assert treatments["production_timeseries"] == "REUSE"
    assert treatments["well_test"] == "REUSE"
    assert treatments["nodal_or_well_model"] == "REUSE"
    assert treatments["flow_network_model"] == "REUSE"
    assert treatments["production_assurance_case"] == "OWN"
    assert treatments["well_operating_envelope"] == "OWN"
    capabilities = {item["id"] for item in contract["runtime_capabilities"]}
    assert {"production.well.timeseries", "production.well_test", "production.well_model", "production.integrity.status", "production.surface.constraint"} <= capabilities
    assert set(contract["executable_journeys"]) == {"PROD-01", "PROD-02", "PROD-06"}


def test_benchmark_is_explicitly_synthetic_and_preserves_external_identity():
    benchmark = _yaml(BENCHMARK)
    assert benchmark["synthetic"] is True
    assert benchmark["provenance"]["source_dataset"] == "none"
    focus = benchmark["focus_well"]
    refs = [focus["external_identity"], focus["deliverability_model"]["source_ref"], focus["operating_envelope"]["source_ref"]]
    refs.extend(item["source_ref"] for item in benchmark["external_evidence"])
    for ref in refs:
        assert ref["source_system"]
        assert ref["record_kind"]
        assert ref["record_id"]
        assert ref["record_version"]


def test_prod01_triages_material_exception_without_misdiagnosing_data_limited_well():
    runtime = ProductionTechnologistRuntime.from_yaml(BENCHMARK)
    result = runtime.execute("PROD-01")
    assert result.status == "ANSWERED"
    assert result.answer is not None
    assert result.answer["attention_order"] == ["P-118", "P-121", "P-115"]
    assert result.answer["wells"]["P-118"]["classification"] == "material_underperformance"
    assert result.answer["wells"]["P-121"]["classification"] == "data_quality_limited"
    assert result.answer["wells"]["P-115"]["classification"] == "normal"


def test_prod02_explains_model_vs_reality_gap_without_recalculating_nodal_hydraulics():
    runtime = ProductionTechnologistRuntime.from_yaml(BENCHMARK)
    result = runtime.execute("PROD-02")
    assert result.status == "ANSWERED"
    answer = result.answer
    assert answer is not None
    assert answer["well"] == "P-118"
    assert answer["expected_deliverability_bopd"] == 6200
    assert answer["actual_stable_rate_bopd"] == 4750
    assert answer["deliverability_gap_bopd"] == 1450
    assert answer["deliverability_gap_fraction"] == 0.234
    assert set(answer["stale_or_violated_assumptions"]) == {"water_cut_fraction", "gas_lift_mmscfd", "surface_backpressure_bar"}
    assert answer["model"]["source_ref"]["record_version"] == "17"
    assert answer["cepio_recalculated_nodal_hydraulics"] is False


def test_prod06_ranks_competing_causes_and_exposes_falsification_for_every_diagnosis():
    runtime = ProductionTechnologistRuntime.from_yaml(BENCHMARK)
    result = runtime.execute("PROD-06")
    assert result.status == "ANSWERED"
    answer = result.answer
    assert answer is not None
    diagnoses = answer["ranked_hypotheses"]
    assert [item["id"] for item in diagnoses] == ["H-BACKPRESSURE", "H-GASLIFT", "H-NEARWELLBORE", "H-DEPLETION"]
    assert diagnoses[0]["confidence"] > diagnoses[1]["confidence"] > diagnoses[2]["confidence"] > diagnoses[3]["confidence"]
    assert all(item["falsification_test"] for item in diagnoses)
    assert any("Current downhole pressure" in gap for gap in answer["material_evidence_gaps"])
    near_wellbore = next(item for item in diagnoses if item["id"] == "H-NEARWELLBORE")
    assert near_wellbore["contradictory_evidence"][0]["id"] == "EV-P118-BHP"
    assert all(step["authority"] == "recommendation_only" for step in answer["recommended_next_steps"])


def test_all_v01_executable_journeys_pass_governed_skill_preflight():
    runtime = ProductionTechnologistRuntime.from_yaml(BENCHMARK)
    coverage = runtime.execute_all()
    assert coverage.complete is True
    assert coverage.answered == 3
    assert coverage.blocked == 0
    for result in coverage.results.values():
        assert result.status == "ANSWERED"
        assert result.preflights
        assert all(preflight.status == "READY" for preflight in result.preflights)
        assert result.human_authority_required is True
        assert "change_live_setpoint" in result.prohibited_ai_conclusions


def test_runtime_fails_closed_for_actor_without_production_read_authority():
    runtime = ProductionTechnologistRuntime.from_yaml(BENCHMARK)
    result = runtime.execute("PROD-06", actor_id="control-agent", actor_roles={"autonomous_control_agent"})
    assert result.status == "BLOCKED"
    assert any(blocker.code == "SKILL_PREFLIGHT_BLOCKED" for blocker in result.blockers)


def test_runtime_fails_closed_when_external_version_identity_is_missing():
    benchmark = _yaml(BENCHMARK)
    broken = deepcopy(benchmark)
    broken["focus_well"]["deliverability_model"]["source_ref"]["record_version"] = ""
    runtime = ProductionTechnologistRuntime(broken, resource_root=ROOT)
    result = runtime.execute("PROD-02")
    assert result.status == "BLOCKED"
    assert any(blocker.code == "INCOMPLETE_EXTERNAL_IDENTITY" for blocker in result.blockers)
