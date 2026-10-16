from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
WF = Namespace("https://cepio.org/ontology/workforce#")
CEPIO = Namespace("https://cepio.org/ontology/core#")


def _graph() -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies/workforce.ttl", format="turtle")
    return graph


def test_workforce_authority_responsibility_and_handover_contracts():
    graph = _graph()

    assert (WF.AuthorityAssignment, RDF.type, OWL.Class) in graph
    assert (WF.AuthorityAssignment, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (WF.ResponsibilityAssignment, RDF.type, OWL.Class) in graph
    assert (WF.ResponsibilityAssignment, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (WF.ShiftHandover, RDF.type, OWL.Class) in graph
    assert (WF.ShiftHandover, RDFS.subClassOf, CEPIO.Event) in graph

    expected_properties = {
        WF.assignmentForActivity: (WF.CrewAssignment, CEPIO.Activity),
        WF.authorityHolder: (WF.AuthorityAssignment, CEPIO.Party),
        WF.authorityForAsset: (WF.AuthorityAssignment, CEPIO.Asset),
        WF.authorityForWork: (WF.AuthorityAssignment, CEPIO.WorkItem),
        WF.responsibilityHolder: (WF.ResponsibilityAssignment, CEPIO.Party),
        WF.responsibilityForAsset: (WF.ResponsibilityAssignment, CEPIO.Asset),
        WF.responsibilityForWork: (WF.ResponsibilityAssignment, CEPIO.WorkItem),
        WF.handoverFromAssignment: (WF.ShiftHandover, WF.CrewAssignment),
        WF.handoverToAssignment: (WF.ShiftHandover, WF.CrewAssignment),
        WF.handoverForActivity: (WF.ShiftHandover, CEPIO.Activity),
        WF.handoverCarriesWork: (WF.ShiftHandover, CEPIO.WorkItem),
    }
    for predicate, (domain, range_) in expected_properties.items():
        assert (predicate, RDF.type, OWL.ObjectProperty) in graph
        assert (predicate, RDFS.domain, domain) in graph
        assert (predicate, RDFS.range, range_) in graph


def test_workforce_module_version_is_0_1_2():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text(encoding="utf-8"))
    modules = {module["id"]: module for module in catalogue["modules"]}
    assert str(modules["workforce"]["version"]) == "0.1.2"


def test_direct_person_shortcuts_are_not_introduced():
    graph = _graph()
    assert (WF.assignedToActivity, RDF.type, OWL.ObjectProperty) not in graph
    assert (WF.responsibleForWork, RDF.type, OWL.ObjectProperty) not in graph
