from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")


def _core_graph() -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / "core.ttl", format="turtle")
    return graph


def test_core_declares_epistemic_primitives():
    graph = _core_graph()
    for class_name in (
        "Evidence",
        "Claim",
        "Hypothesis",
        "Assumption",
        "Assessment",
        "UncertaintyAssessment",
        "ConfidenceAssessment",
        "InformationGain",
        "Dependency",
    ):
        assert (CEPIO[class_name], RDF.type, OWL.Class) in graph


def test_claim_and_assessment_inheritance_is_explicit():
    graph = _core_graph()
    assert (CEPIO.Hypothesis, RDFS.subClassOf, CEPIO.Claim) in graph
    assert (CEPIO.Assumption, RDFS.subClassOf, CEPIO.Claim) in graph
    assert (CEPIO.UncertaintyAssessment, RDFS.subClassOf, CEPIO.Assessment) in graph
    assert (CEPIO.ConfidenceAssessment, RDFS.subClassOf, CEPIO.Assessment) in graph
    assert (CEPIO.InformationGain, RDFS.subClassOf, CEPIO.Assessment) in graph


def test_uncertainty_relationship_contract_is_explicit():
    graph = _core_graph()
    assert (CEPIO.supportedBy, RDFS.domain, CEPIO.Claim) in graph
    assert (CEPIO.supportedBy, RDFS.range, CEPIO.Evidence) in graph
    assert (CEPIO.assesses, RDFS.domain, CEPIO.Assessment) in graph
    assert (CEPIO.hasUncertaintyAssessment, RDFS.range, CEPIO.UncertaintyAssessment) in graph
    assert (CEPIO.hasConfidenceAssessment, RDFS.range, CEPIO.ConfidenceAssessment) in graph
    assert (CEPIO.reducesUncertainty, RDFS.domain, CEPIO.Evidence) in graph
    assert (CEPIO.reducesUncertainty, RDFS.range, CEPIO.UncertaintyAssessment) in graph
    assert (CEPIO.correlatedWith, RDF.type, OWL.SymmetricProperty) in graph


def test_dependency_is_reified_for_richer_domain_profiles():
    graph = _core_graph()
    assert (CEPIO.dependencySource, RDFS.domain, CEPIO.Dependency) in graph
    assert (CEPIO.dependencyTarget, RDFS.domain, CEPIO.Dependency) in graph
    assert (CEPIO.dependencySource, RDFS.range, CEPIO.Entity) in graph
    assert (CEPIO.dependencyTarget, RDFS.range, CEPIO.Entity) in graph
