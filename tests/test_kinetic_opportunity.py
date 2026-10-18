from pathlib import Path

from rdflib import Graph, Namespace, OWL, RDF, RDFS

ROOT = Path(__file__).parents[1]
KIN = Namespace("https://cepio.org/ontology/kinetic#")
CEPIO = Namespace("https://cepio.org/ontology/core#")


def _graph() -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / "kinetic.ttl", format="turtle")
    return graph


def test_opportunity_option_and_option_recommendation_are_kinetic_entities():
    graph = _graph()
    for concept in (KIN.Opportunity, KIN.Option, KIN.OptionRecommendation):
        assert (concept, RDF.type, OWL.Class) in graph
        assert (concept, RDFS.subClassOf, CEPIO.Entity) in graph


def test_opportunity_is_linked_to_objective_and_options():
    graph = _graph()
    assert (KIN.opportunityForObjective, RDFS.domain, KIN.Opportunity) in graph
    assert (KIN.opportunityForObjective, RDFS.range, CEPIO.Objective) in graph
    assert (KIN.hasOption, RDFS.domain, KIN.Opportunity) in graph
    assert (KIN.hasOption, RDFS.range, KIN.Option) in graph


def test_option_recommendation_is_not_a_decision():
    graph = _graph()
    assert (KIN.hasRecommendation, RDFS.range, KIN.OptionRecommendation) in graph
    assert (KIN.recommendsOption, RDFS.domain, KIN.OptionRecommendation) in graph
    assert (KIN.recommendsOption, RDFS.range, KIN.Option) in graph
    assert (KIN.OptionRecommendation, RDFS.subClassOf, KIN.Decision) not in graph


def test_decision_can_address_opportunity_and_select_option():
    graph = _graph()
    assert (KIN.addressesOpportunity, RDFS.domain, KIN.Decision) in graph
    assert (KIN.addressesOpportunity, RDFS.range, KIN.Opportunity) in graph
    assert (KIN.selectedOption, RDFS.domain, KIN.Decision) in graph
    assert (KIN.selectedOption, RDFS.range, KIN.Option) in graph
    assert (KIN.basedOnRecommendation, RDFS.domain, KIN.Decision) in graph
    assert (KIN.basedOnRecommendation, RDFS.range, KIN.OptionRecommendation) in graph
