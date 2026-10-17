from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
HSE = Namespace("https://cepio.org/ontology/hse#")
PERF = Namespace("https://cepio.org/ontology/performance#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_safety_barrier_and_impairment_are_reusable_hse_semantics():
    graph = _graph("hse.ttl")
    assert (HSE.SafetyBarrier, RDF.type, OWL.Class) in graph
    assert (HSE.SafetyBarrier, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (HSE.BarrierImpairment, RDF.type, OWL.Class) in graph
    assert (HSE.BarrierImpairment, RDFS.subClassOf, CEPIO.State) in graph
    assert (HSE.impairmentOfBarrier, RDFS.domain, HSE.BarrierImpairment) in graph
    assert (HSE.impairmentOfBarrier, RDFS.range, HSE.SafetyBarrier) in graph
    # Restoration continues to reuse the existing common corrective-action pattern.
    assert (HSE.barrierRestorationWork, RDF.type, OWL.ObjectProperty) not in graph


def test_management_of_change_reuses_common_work_and_authority_patterns():
    graph = _graph("hse.ttl")
    assert (HSE.ManagementOfChange, RDF.type, OWL.Class) in graph
    assert (HSE.ManagementOfChange, RDFS.subClassOf, CEPIO.WorkItem) in graph
    assert (HSE.changeAffectsAsset, RDFS.domain, HSE.ManagementOfChange) in graph
    assert (HSE.changeAffectsAsset, RDFS.range, CEPIO.Asset) in graph
    # MOC-specific approval/authority shortcuts are intentionally absent.
    assert (HSE.mocApprovedBy, RDF.type, OWL.ObjectProperty) not in graph
    assert (HSE.mocAuthorityHolder, RDF.type, OWL.ObjectProperty) not in graph


def test_production_loss_is_common_performance_measurement():
    graph = _graph("performance.ttl")
    assert (PERF.ProductionLoss, RDF.type, OWL.Class) in graph
    assert (PERF.ProductionLoss, RDFS.subClassOf, CEPIO.Measurement) in graph
    assert (PERF.ProcessProductionLoss, RDF.type, OWL.Class) not in graph


def test_refinery_core_remediation_bumps_only_affected_common_modules():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    versions = {module["id"]: str(module["version"]) for module in catalogue["modules"]}
    assert versions["hse"] == "0.1.2"
    assert versions["performance"] == "0.1.1"
    assert versions["process_industry"] == "0.1.0"
