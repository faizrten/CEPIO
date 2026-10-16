from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
HSE = Namespace("https://cepio.org/ontology/hse#")
WF = Namespace("https://cepio.org/ontology/workforce#")
SUPPLY = Namespace("https://cepio.org/ontology/supply#")
ENT = Namespace("https://cepio.org/ontology/enterprise#")
IND = Namespace("https://cepio.org/ontology/industrial#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_energy_isolation_is_common_hse_work_control():
    graph = _graph("hse.ttl")
    assert (HSE.EnergyIsolation, RDF.type, OWL.Class) in graph
    assert (HSE.EnergyIsolation, RDFS.subClassOf, CEPIO.WorkItem) in graph
    assert (HSE.isolationForAsset, RDFS.domain, HSE.EnergyIsolation) in graph
    assert (HSE.isolationForAsset, RDFS.range, CEPIO.Asset) in graph
    assert (HSE.isolationGovernsWork, RDFS.range, CEPIO.WorkItem) in graph
    assert (HSE.isolationIssuedBy, RDFS.range, CEPIO.Party) in graph
    assert (HSE.isolationVerifiedBy, RDFS.range, CEPIO.Party) in graph


def test_crew_rotation_preserves_assignment_context():
    graph = _graph("workforce.ttl")
    assert (WF.CrewRotation, RDF.type, OWL.Class) in graph
    assert (WF.CrewRotation, RDFS.subClassOf, CEPIO.Activity) in graph
    assert (WF.rotationForAsset, RDFS.range, CEPIO.Asset) in graph
    assert (WF.rotationFromAssignment, RDFS.range, WF.CrewAssignment) in graph
    assert (WF.rotationToAssignment, RDFS.range, WF.CrewAssignment) in graph
    # Mobilization readiness is deliberately derived rather than stored as a specialized class.
    assert (WF.MobilizationConstraint, RDF.type, OWL.Class) not in graph


def test_purchase_order_connects_supplier_requirement_and_spare():
    graph = _graph("supply.ttl")
    assert (SUPPLY.PurchaseOrder, RDF.type, OWL.Class) in graph
    assert (SUPPLY.PurchaseOrder, RDFS.subClassOf, CEPIO.WorkItem) in graph
    assert (SUPPLY.purchaseOrderSupplier, RDFS.range, ENT.Supplier) in graph
    assert (SUPPLY.purchaseOrderForRequirement, RDFS.range, SUPPLY.MaterialRequirement) in graph
    assert (SUPPLY.purchaseOrderForSpare, RDFS.range, IND.SparePart) in graph


def test_common_module_versions_are_bumped_additively():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    versions = {module["id"]: str(module["version"]) for module in catalogue["modules"]}
    assert versions["hse"] == "0.1.1"
    assert versions["supply"] == "0.1.1"
    assert versions["workforce"] == "0.1.3"
