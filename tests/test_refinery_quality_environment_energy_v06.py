from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
KIN = Namespace("https://cepio.org/ontology/kinetic#")
MFG = Namespace("https://cepio.org/ontology/manufacturing#")
PROCESS = Namespace("https://cepio.org/ontology/process#")
PERF = Namespace("https://cepio.org/ontology/performance#")
IND = Namespace("https://cepio.org/ontology/industrial#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def _normalizer_module():
    path = ROOT / "scripts" / "build_refinery_normalized_benchmark.py"
    spec = spec_from_file_location("refinery_normalizer", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_reuses_material_specification_and_adds_explicit_disposition():
    graph = _graph("manufacturing.ttl")

    assert (MFG.MaterialSpecification, RDF.type, OWL.Class) in graph
    assert (MFG.QualityDisposition, RDF.type, OWL.Class) in graph
    assert (MFG.QualityDisposition, RDFS.subClassOf, CEPIO.WorkItem) in graph

    assert (MFG.lotEvaluatedAgainstSpecification, RDF.type, OWL.ObjectProperty) in graph
    assert (MFG.lotEvaluatedAgainstSpecification, RDFS.domain, MFG.MaterialLot) in graph
    assert (MFG.lotEvaluatedAgainstSpecification, RDFS.range, MFG.MaterialSpecification) in graph
    assert (MFG.dispositionForLot, RDFS.domain, MFG.QualityDisposition) in graph
    assert (MFG.dispositionForLot, RDFS.range, MFG.MaterialLot) in graph

    # Phase 6 explicitly rejects a duplicate generic specification class and a
    # relationship that would assert conformance for an off-spec lot.
    assert (MFG.Specification, RDF.type, OWL.Class) not in graph
    assert (MFG.lotConformsToSpecification, RDF.type, OWL.ObjectProperty) not in graph


def test_emission_observation_can_be_evaluated_against_applicable_limit():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.EmissionLimit, RDF.type, OWL.Class) in graph
    assert (PROCESS.EmissionLimit, RDFS.subClassOf, KIN.Constraint) in graph
    assert (PROCESS.evaluatedAgainstEmissionLimit, RDF.type, OWL.ObjectProperty) in graph
    assert (PROCESS.evaluatedAgainstEmissionLimit, RDFS.domain, PROCESS.EmissionObservation) in graph
    assert (PROCESS.evaluatedAgainstEmissionLimit, RDFS.range, PROCESS.EmissionLimit) in graph
    assert (PROCESS.emissionFromUnit, RDFS.range, IND.ProcessUnit) in graph


def test_energy_intensity_remains_metric_mapping_not_class_per_kpi():
    perf_graph = _graph("performance.ttl")
    assert (PERF.EnergyIntensityKPI, RDF.type, OWL.Class) not in perf_graph

    mapping = yaml.safe_load((ROOT / "mappings" / "performance_kpis.yaml").read_text(encoding="utf-8"))
    packaged = yaml.safe_load(
        (ROOT / "src" / "cepio" / "resources" / "mappings" / "performance_kpis.yaml").read_text(encoding="utf-8")
    )
    by_id = {item["id"]: item for item in mapping["metric_mappings"]}
    energy = by_id["energy-intensity"]

    assert energy["canonical_type"] == "https://cepio.org/ontology/core#KPI"
    assert energy["observation_type"] == "https://cepio.org/ontology/performance#KPIObservation"
    assert "iso-50001-2018" in energy["standards"]
    assert energy["semantics"]["formula_is_external"] is True
    assert energy["semantics"]["denominator_is_external"] is True
    assert packaged == mapping


def test_normalized_benchmark_v012_uses_canonical_quality_and_kpi_patterns():
    raw = yaml.safe_load(
        (ROOT / "generalization" / "competency" / "refinery-process-manufacturing-v0.1.yaml").read_text(encoding="utf-8")
    )
    pack = _normalizer_module().normalize(raw)
    assert pack["id"] == "refinery-process-manufacturing-capabilities-v0.1.2"
    assert pack["version"] == "0.1.2"

    by_question = {item["id"]: item for item in pack["questions"]}
    rp8 = {item["id"]: item for item in by_question["RP-PC-008"]["capabilities"]}
    lot_alt = rp8["lot-specification"]["alternatives"][0]
    disposition_alt = rp8["quality-disposition"]["alternatives"][0]

    assert {item["iri"] for item in lot_alt["terms"]} == {
        "https://cepio.org/ontology/manufacturing#MaterialLot",
        "https://cepio.org/ontology/manufacturing#MaterialSpecification",
    }
    assert lot_alt["edges"][0]["predicate"] == "https://cepio.org/ontology/manufacturing#lotEvaluatedAgainstSpecification"
    assert disposition_alt["edges"][0]["predicate"] == "https://cepio.org/ontology/manufacturing#dispositionForLot"

    rp10 = {item["id"]: item for item in by_question["RP-PC-010"]["capabilities"]}
    energy_alt = rp10["energy-intensity"]["alternatives"][0]
    assert energy_alt["terms"] == [{"iri": "https://cepio.org/ontology/core#KPI", "kind": "class"}]
    assert energy_alt["edges"][0]["target"] == "https://cepio.org/ontology/core#KPI"


def test_phase6_versions_only_changed_ontology_modules():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text(encoding="utf-8"))
    modules = {item["id"]: item for item in catalogue["modules"]}

    assert str(modules["manufacturing"]["version"]) == "0.1.1"
    assert str(modules["process_industry"]["version"]) == "0.1.6"
    assert str(modules["performance"]["version"]) == "0.1.2"
