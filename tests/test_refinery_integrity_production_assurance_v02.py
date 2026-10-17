from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
IND = Namespace("https://cepio.org/ontology/industrial#")
REL = Namespace("https://cepio.org/ontology/reliability#")
PERF = Namespace("https://cepio.org/ontology/performance#")
PROCESS = Namespace("https://cepio.org/ontology/process#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_damage_mechanism_and_rbi_are_reusable_reliability_semantics():
    graph = _graph("reliability.ttl")

    assert (REL.DamageMechanism, RDF.type, OWL.Class) in graph
    assert (REL.DamageMechanism, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (REL.RiskBasedInspectionAssessment, RDF.type, OWL.Class) in graph
    assert (REL.RiskBasedInspectionAssessment, RDFS.subClassOf, CEPIO.Risk) in graph

    assert (REL.damageMechanismForEquipment, RDF.type, OWL.ObjectProperty) in graph
    assert (REL.damageMechanismForEquipment, RDFS.domain, REL.DamageMechanism) in graph
    assert (REL.damageMechanismForEquipment, RDFS.range, IND.Equipment) in graph

    assert (REL.assessmentForEquipment, RDFS.domain, REL.RiskBasedInspectionAssessment) in graph
    assert (REL.assessmentForEquipment, RDFS.range, IND.Equipment) in graph
    assert (REL.assessmentConsidersDamageMechanism, RDFS.range, REL.DamageMechanism) in graph
    assert (REL.assessmentUsesInspection, RDFS.range, IND.Inspection) in graph


def test_integrity_operating_window_specializes_existing_process_envelope():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.IntegrityOperatingWindow, RDF.type, OWL.Class) in graph
    assert (PROCESS.IntegrityOperatingWindow, RDFS.subClassOf, PROCESS.OperatingEnvelope) in graph

    # IOW excursions reuse the existing ProcessDeviation -> OperatingEnvelope
    # semantics instead of creating a second event/state hierarchy.
    assert (PROCESS.deviationAgainstEnvelope, RDFS.domain, PROCESS.ProcessDeviation) in graph
    assert (PROCESS.deviationAgainstEnvelope, RDFS.range, PROCESS.OperatingEnvelope) in graph
    assert (PROCESS.IntegrityOperatingWindowExcursion, RDF.type, OWL.Class) not in graph
    assert (PROCESS.iowExcursionAgainstWindow, RDF.type, OWL.ObjectProperty) not in graph


def test_production_capacity_is_common_measurement_not_kpi_class_proliferation():
    graph = _graph("performance.ttl")

    assert (PERF.ProductionCapacity, RDF.type, OWL.Class) in graph
    assert (PERF.ProductionCapacity, RDFS.subClassOf, CEPIO.Measurement) in graph
    assert (PERF.ProductionLoss, RDFS.subClassOf, CEPIO.Measurement) in graph

    # Availability remains an instance/formula of the generic KPI contract and
    # belongs in metric mappings rather than a class-per-KPI ontology taxonomy.
    assert (CEPIO.KPI, RDF.type, OWL.Class) in _graph("core.ttl")
    assert (PERF.AvailabilityKPI, RDF.type, OWL.Class) not in graph


def test_assurance_slice_is_additively_versioned_without_cross_tier_coupling():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    modules = {item["id"]: item for item in catalogue["modules"]}

    assert str(modules["reliability"]["version"]) == "0.1.1"
    assert str(modules["performance"]["version"]) == "0.1.2"
    assert str(modules["process_industry"]["version"]) == "0.1.3"
    assert modules["reliability"]["tier"] == "industrial-common"
    assert modules["performance"]["tier"] == "industrial-common"
    assert modules["process_industry"]["tier"] == "domain"

    reliability_text = (ROOT / "ontologies" / "reliability.ttl").read_text(encoding="utf-8")
    performance_text = (ROOT / "ontologies" / "performance.ttl").read_text(encoding="utf-8")
    assert "https://cepio.org/ontology/process#" not in reliability_text
    assert "https://cepio.org/ontology/process#" not in performance_text
