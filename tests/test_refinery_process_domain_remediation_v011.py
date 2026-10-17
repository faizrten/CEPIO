from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
IND = Namespace("https://cepio.org/ontology/industrial#")
KIN = Namespace("https://cepio.org/ontology/kinetic#")
PROCESS = Namespace("https://cepio.org/ontology/process#")


def _process_graph() -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / "process_industry.ttl", format="turtle")
    return graph


def test_process_constraint_reuses_common_constraint_semantics():
    graph = _process_graph()
    assert (PROCESS.ProcessConstraint, RDF.type, OWL.Class) in graph
    assert (PROCESS.ProcessConstraint, RDFS.subClassOf, KIN.Constraint) in graph
    assert (PROCESS.constraintOnUnit, RDF.type, OWL.ObjectProperty) in graph
    assert (PROCESS.constraintOnUnit, RDFS.domain, PROCESS.ProcessConstraint) in graph
    assert (PROCESS.constraintOnUnit, RDFS.range, IND.ProcessUnit) in graph


def test_operating_envelope_and_limit_are_process_domain_semantics():
    graph = _process_graph()
    assert (PROCESS.OperatingEnvelope, RDF.type, OWL.Class) in graph
    assert (PROCESS.OperatingEnvelope, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (PROCESS.OperatingLimit, RDF.type, OWL.Class) in graph
    assert (PROCESS.OperatingLimit, RDFS.subClassOf, KIN.Constraint) in graph
    assert (PROCESS.envelopeForUnit, RDF.type, OWL.ObjectProperty) in graph
    assert (PROCESS.envelopeForUnit, RDFS.domain, PROCESS.OperatingEnvelope) in graph
    assert (PROCESS.envelopeForUnit, RDFS.range, IND.ProcessUnit) in graph


def test_process_deviation_is_temporal_state_against_an_operating_envelope():
    graph = _process_graph()
    assert (PROCESS.ProcessDeviation, RDF.type, OWL.Class) in graph
    assert (PROCESS.ProcessDeviation, RDFS.subClassOf, CEPIO.State) in graph
    assert (PROCESS.deviationAgainstEnvelope, RDF.type, OWL.ObjectProperty) in graph
    assert (PROCESS.deviationAgainstEnvelope, RDFS.domain, PROCESS.ProcessDeviation) in graph
    assert (PROCESS.deviationAgainstEnvelope, RDFS.range, PROCESS.OperatingEnvelope) in graph


def test_startup_or_restart_reuses_activity_dependency_and_approval_contracts():
    process_graph = _process_graph()
    core_graph = Graph().parse(ROOT / "ontologies" / "core.ttl", format="turtle")
    kinetic_graph = Graph().parse(ROOT / "ontologies" / "kinetic.ttl", format="turtle")

    assert (PROCESS.StartupOrRestart, RDF.type, OWL.Class) in process_graph
    assert (PROCESS.StartupOrRestart, RDFS.subClassOf, CEPIO.Activity) in process_graph
    assert (CEPIO.dependsOn, RDF.type, OWL.ObjectProperty) in core_graph
    assert (KIN.requiresApproval, RDF.type, OWL.ObjectProperty) in kinetic_graph

    # Restart readiness composes existing dependency/approval semantics rather than
    # proliferating restart-specific control predicates.
    assert (PROCESS.restartDependsOnPermit, RDF.type, OWL.ObjectProperty) not in process_graph
    assert (PROCESS.restartRequiresApproval, RDF.type, OWL.ObjectProperty) not in process_graph


def test_process_industry_module_is_additively_versioned_and_depends_on_kinetic():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    module = next(item for item in catalogue["modules"] if item["id"] == "process_industry")
    assert str(module["version"]) == "0.1.3"
    dependencies = {item["module"] for item in module["depends_on"]}
    assert {"core", "industrial", "asset", "kinetic"}.issubset(dependencies)


def test_process_domain_does_not_duplicate_canonical_process_unit_identity():
    graph = _process_graph()
    assert (PROCESS.ProcessUnit, RDF.type, OWL.Class) not in graph
