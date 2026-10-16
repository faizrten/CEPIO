from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
DRILL = Namespace("https://cepio.org/ontology/drilling#")


def _graph() -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / "drilling.ttl", format="turtle")
    return graph


def test_drilling_fluid_observation_reuses_common_measurement_semantics():
    graph = _graph()
    assert (DRILL.DrillingFluidObservation, RDF.type, OWL.Class) in graph
    assert (DRILL.DrillingFluidObservation, RDFS.subClassOf, CEPIO.Measurement) in graph
    # Do not duplicate the canonical Entity -> measuredBy -> Measurement contract.
    assert (DRILL.observationForActivity, RDF.type, OWL.ObjectProperty) not in graph


def test_cementing_execution_has_source_neutral_program_semantics():
    graph = _graph()
    assert (DRILL.CementingJob, RDF.type, OWL.Class) in graph
    assert (DRILL.CementingJob, RDFS.subClassOf, DRILL.ActivityInterval) in graph
    assert (DRILL.CementProgram, RDFS.subClassOf, CEPIO.Document) in graph
    assert (DRILL.executesProgram, RDFS.domain, DRILL.CementingJob) in graph
    assert (DRILL.executesProgram, RDFS.range, DRILL.CementProgram) in graph
    assert (DRILL.ServiceDeliveryEvidence, RDF.type, OWL.Class) not in graph


def test_marine_support_asset_reuses_dependency_semantics():
    graph = _graph()
    assert (DRILL.MarineSupportAsset, RDF.type, OWL.Class) in graph
    assert (DRILL.MarineSupportAsset, RDFS.subClassOf, CEPIO.PhysicalAsset) in graph
    assert (DRILL.supportedByMarineAsset, RDF.type, OWL.ObjectProperty) not in graph


def test_drilling_module_version_is_0_1_2():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    versions = {module["id"]: str(module["version"]) for module in catalogue["modules"]}
    assert versions["drilling"] == "0.1.2"
