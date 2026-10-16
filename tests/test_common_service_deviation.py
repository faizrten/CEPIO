from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
COMM = Namespace("https://cepio.org/ontology/commercial#")
WORK = Namespace("https://cepio.org/ontology/work#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_service_delivery_is_common_commercial_semantics():
    graph = _graph("commercial.ttl")
    assert (COMM.ServiceExecution, RDFS.subClassOf, CEPIO.Activity) in graph
    assert (COMM.ServiceDeliveryEvidence, RDFS.subClassOf, CEPIO.Document) in graph
    assert (COMM.ServiceAcceptance, RDFS.subClassOf, CEPIO.Event) in graph
    assert (COMM.serviceExecutionForActivity, RDFS.range, CEPIO.Activity) in graph
    assert (COMM.performedBy, RDFS.range, CEPIO.Party) in graph
    assert (COMM.governedByObligation, RDFS.range, COMM.ContractObligation) in graph
    assert (COMM.producesDeliveryEvidence, RDFS.range, COMM.ServiceDeliveryEvidence) in graph
    assert (COMM.acceptanceOfService, RDFS.range, COMM.ServiceExecution) in graph
    assert (COMM.acceptedBy, RDFS.range, CEPIO.Party) in graph


def test_plan_deviation_reuses_generic_impacts_and_authority_patterns():
    graph = _graph("work_management.ttl")
    assert (WORK.PlanDeviation, RDF.type, OWL.Class) in graph
    assert (WORK.PlanDeviation, RDFS.subClassOf, CEPIO.WorkItem) in graph
    assert (WORK.deviationFromPlan, RDFS.domain, WORK.PlanDeviation) in graph
    assert (WORK.deviationFromPlan, RDFS.range, CEPIO.Document) in graph
    # No drilling-only ProgramDeviation or approval predicate is introduced here.


def test_service_and_work_module_versions_are_bumped():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    versions = {module["id"]: str(module["version"]) for module in catalogue["modules"]}
    assert versions["work_management"] == "0.1.1"
    assert versions["commercial"] == "0.1.2"
