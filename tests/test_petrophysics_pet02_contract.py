from pathlib import Path

import yaml
from rdflib import Graph, Namespace, OWL, RDF, RDFS


ROOT = Path(__file__).parents[1]
PERSONA = ROOT / "generalization" / "personas" / "subsurface-petrophysics-v0.1.yaml"
CONTRACT = ROOT / "generalization" / "competency" / "subsurface-petrophysics-pet02-v0.1.yaml"
BENCHMARK = ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-pet02-a17-zone-b.yaml"
ONTOLOGY = ROOT / "ontologies" / "subsurface.ttl"
MODULES = ROOT / "ontology-modules.yaml"

CEPIO = Namespace("https://cepio.org/ontology/core#")
SUB = Namespace("https://cepio.org/ontology/subsurface#")
ENERGY = Namespace("https://cepio.org/ontology/energy#")


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_subsurface_module_is_registered_as_experimental_domain_module():
    catalogue = _yaml(MODULES)
    assert "subsurface" in catalogue["architecture"]["domain"]
    module = next(item for item in catalogue["modules"] if item["id"] == "subsurface")
    assert module["version"] == "0.2.0"
    assert module["stability"] == "experimental"
    assert {dependency["module"] for dependency in module["depends_on"]} == {"core", "energy"}


def test_pet02_ontology_models_case_characteristics_and_authority_state_without_osdu_payloads():
    graph = Graph().parse(ONTOLOGY, format="turtle")

    assert (SUB.FormationEvaluationCase, RDF.type, OWL.Class) in graph
    assert (SUB.FormationEvaluationCase, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (SUB.PetrophysicalCharacteristic, RDFS.subClassOf, CEPIO.Entity) in graph

    for characteristic in (
        SUB.EffectivePorosityCharacteristic,
        SUB.WaterSaturationCharacteristic,
        SUB.PermeabilityCharacteristic,
        SUB.NetReservoirCharacteristic,
        SUB.NetPayCharacteristic,
        SUB.FluidContactCharacteristic,
    ):
        assert (characteristic, RDFS.subClassOf, SUB.PetrophysicalCharacteristic) in graph

    assert (SUB.caseForWell, RDFS.range, ENERGY.Well) in graph
    assert (SUB.hasCharacteristic, RDFS.range, SUB.PetrophysicalCharacteristic) in graph
    assert (SUB.hasFormationEvaluationState, RDFS.range, SUB.FormationEvaluationState) in graph

    for state in (
        SUB.Draft,
        SUB.UnderReview,
        SUB.Approved,
        SUB.Authoritative,
        SUB.Superseded,
        SUB.Rejected,
    ):
        assert (state, RDF.type, SUB.FormationEvaluationState) in graph

    serialized = ONTOLOGY.read_text()
    assert "WellLog" not in serialized
    assert "RAFS" not in serialized
    assert "RESQML" not in serialized


def test_persona_is_decision_role_focused_and_ai_authority_fails_closed():
    persona = _yaml(PERSONA)
    assert persona["persona"]["id"] == "petrophysicist"
    journeys = {item["id"]: item for item in persona["journeys"]}
    assert journeys["PET-02"]["reference"] is True
    assert journeys["PET-02"]["role"] == "primary"

    authority = persona["persona"]["authority"]
    assert "recommend interpretation changes" in authority["may"]
    assert "declare interpretation authoritative" in authority["must_handoff"]
    assert "overwrite OSDU or ADME technical records" in authority["must_handoff"]


def test_pet02_contract_preserves_osdu_boundary_and_core_epistemic_semantics():
    contract = _yaml(CONTRACT)
    assert contract["journey_id"] == "PET-02"
    treatments = {
        item["id"]: item["treatment"] for item in contract["semantic_boundary"]["objects"]
    }
    assert treatments["well"] == "BIND"
    assert treatments["wellbore"] == "REUSE"
    assert treatments["well_log"] == "REUSE"
    assert treatments["rock_fluid_sample_or_analysis"] == "REUSE"
    assert treatments["petrophysical_interpretation_record"] == "EXTEND"
    assert treatments["formation_evaluation_case"] == "OWN"
    assert treatments["petrophysical_characteristic"] == "OWN"

    owned_types = {
        item.get("cepio_type")
        for item in contract["semantic_boundary"]["objects"]
        if item["treatment"] == "OWN"
    }
    assert "https://cepio.org/ontology/core#Evidence" in owned_types
    assert "https://cepio.org/ontology/core#Assumption" in owned_types
    assert "https://cepio.org/ontology/core#UncertaintyAssessment" in owned_types
    assert "https://cepio.org/ontology/core#ConfidenceAssessment" in owned_types


def test_pet02_first_skill_pack_is_bounded_and_recommendation_only():
    contract = _yaml(CONTRACT)
    skills = {item["id"]: item for item in contract["skills"]}
    expected = {
        "cepio.skill.subsurface.petrophysics.formation-evaluation-context",
        "cepio.skill.subsurface.petrophysics.interpretation-delta",
        "cepio.skill.subsurface.petrophysics.assumption-trace",
        "cepio.skill.subsurface.petrophysics.core-log-reconciliation",
        "cepio.skill.subsurface.petrophysics.downstream-impact",
    }
    assert set(skills) == expected
    assert all(skill["authority"] == "recommend_only" for skill in skills.values())

    ai = contract["human_authority"]["ai_skill"]
    assert "recommend" in ai["may"]
    assert "declare_authoritative" in ai["may_not"]
    assert "overwrite_external_record" in ai["may_not"]


def test_benchmark_has_authoritative_and_superseded_revisions_with_expected_delta():
    benchmark = _yaml(BENCHMARK)
    cases = {item["id"]: item for item in benchmark["formation_evaluation_cases"]}
    assert cases["FE-A17-ZB-v3"]["state"] == "https://cepio.org/ontology/subsurface#Authoritative"
    assert cases["FE-A17-ZB-v3"]["supersedes"] == "FE-A17-ZB-v2"
    assert cases["FE-A17-ZB-v2"]["state"] == "https://cepio.org/ontology/subsurface#Superseded"

    changed_assumptions = {
        item["name"] for item in benchmark["expected_interpretation_delta"]["changed_assumptions"]
    }
    assert {
        "rw_ohm_m",
        "archie_m",
        "porosity_cutoff_fraction",
        "permeability_transform",
    } <= changed_assumptions
    changed_findings = {
        item["name"] for item in benchmark["expected_interpretation_delta"]["changed_findings"]
    }
    assert {"water_saturation_fraction", "net_pay_m", "fluid_contact_tvdss_m"} <= changed_findings


def test_external_evidence_preserves_record_and_version_identity_and_contains_a_real_conflict():
    benchmark = _yaml(BENCHMARK)
    evidence = {item["id"]: item for item in benchmark["external_evidence"]}
    for item in evidence.values():
        ref = item["source_ref"]
        assert ref["source_system"]
        assert ref["source_service"]
        assert ref["record_kind"]
        assert ref["record_id"]
        assert ref["record_version"]

    conflict = evidence["EV-CORE-RCA"]
    assert conflict["role"] == "contradictory"
    assert conflict["observed_permeability_md"] == 71
    current = next(
        item for item in benchmark["formation_evaluation_cases"] if item["id"] == "FE-A17-ZB-v3"
    )
    assert conflict["observed_permeability_md"] < current["findings"]["permeability_md"]


def test_benchmark_exposes_decision_relevant_uncertainty_and_downstream_impact():
    benchmark = _yaml(BENCHMARK)
    uncertainty = {item["assesses"] for item in benchmark["uncertainty_assessments"]}
    assert {"water_saturation", "fluid_contact"} <= uncertainty

    downstream = {item["id"]: item for item in benchmark["downstream_dependencies"]}
    assert downstream["SM18"]["depends_on"] == "FE-A17-ZB-v3"
    assert "FE-A17-ZB-v3" in downstream["RC26"]["depends_on"]
    assert "FE-A17-ZB-v3" in downstream["OP-118"]["depends_on"]
    assert "OP-118" in downstream["DEC-INFILL-R3-2026"]["depends_on"]

    expected = benchmark["expected_answer"]
    assert expected["authoritative_case"] == "FE-A17-ZB-v3"
    assert expected["superseded_case"] == "FE-A17-ZB-v2"
    assert expected["contradictory_evidence"] == ["EV-CORE-RCA"]
    assert set(expected["impacted_downstream"]) == {
        "SM18",
        "RM21",
        "RC26",
        "OP-118",
        "DEC-INFILL-R3-2026",
    }
    assert expected["prohibited_ai_conclusion"] == "declare_authoritative"
