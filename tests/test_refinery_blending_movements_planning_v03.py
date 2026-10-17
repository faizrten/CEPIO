from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
MFG = Namespace("https://cepio.org/ontology/manufacturing#")
PROCESS = Namespace("https://cepio.org/ontology/process#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def _version_tuple(value: object) -> tuple[int, ...]:
    return tuple(int(part) for part in str(value).split("."))


def test_crude_assay_is_canonical_but_yield_model_remains_outside_ontology():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.CrudeAssay, RDF.type, OWL.Class) in graph
    assert (PROCESS.CrudeAssay, RDFS.subClassOf, CEPIO.Document) in graph
    assert (PROCESS.characterizesStream, RDFS.domain, PROCESS.CrudeAssay) in graph
    assert (PROCESS.characterizesStream, RDFS.range, PROCESS.MaterialStream) in graph

    # The accepted v0.2 triage classifies executable yield models as a
    # model-registry / mapping-layer concern, not canonical ontology vocabulary.
    assert (PROCESS.YieldModel, RDF.type, OWL.Class) not in graph
    assert (PROCESS.yieldModelForStream, RDF.type, OWL.ObjectProperty) not in graph
    assert (PROCESS.yieldModelForUnit, RDF.type, OWL.ObjectProperty) not in graph

    mapping = yaml.safe_load((ROOT / "mappings" / "process_models.yaml").read_text())
    packaged_mapping = yaml.safe_load(
        (ROOT / "src" / "cepio" / "resources" / "mappings" / "process_models.yaml").read_text()
    )
    yield_model = mapping["model_mappings"][0]
    assert yield_model["id"] == "yield-model"
    assert yield_model["canonical_type"] == "https://cepio.org/ontology/core#DigitalAsset"
    assert yield_model["semantics"]["execution_is_external"] is True
    assert packaged_mapping == mapping


def test_blend_plan_reuses_isa95_schedule_and_material_lot_semantics():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.BlendPlan, RDF.type, OWL.Class) in graph
    assert (PROCESS.BlendPlan, RDFS.subClassOf, CEPIO.Document) in graph
    assert (PROCESS.blendPlanForSchedule, RDFS.domain, PROCESS.BlendPlan) in graph
    assert (PROCESS.blendPlanForSchedule, RDFS.range, MFG.OperationsSchedule) in graph
    assert (PROCESS.blendPlanUsesLot, RDFS.range, MFG.MaterialLot) in graph

    # Do not duplicate generic ISA-95 storage, lot, or schedule concepts in the
    # process namespace merely to satisfy refinery terminology.
    assert (PROCESS.StorageUnit, RDF.type, OWL.Class) not in graph
    assert (PROCESS.MaterialLot, RDF.type, OWL.Class) not in graph
    assert (PROCESS.OperationsSchedule, RDF.type, OWL.Class) not in graph


def test_material_movement_and_transfer_route_form_a_reusable_bulk_transfer_graph():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.MaterialMovement, RDF.type, OWL.Class) in graph
    assert (PROCESS.MaterialMovement, RDFS.subClassOf, CEPIO.Activity) in graph
    assert (PROCESS.TransferRoute, RDF.type, OWL.Class) in graph
    assert (PROCESS.TransferRoute, RDFS.subClassOf, CEPIO.Entity) in graph

    assert (PROCESS.movementFromStorage, RDFS.domain, PROCESS.MaterialMovement) in graph
    assert (PROCESS.movementFromStorage, RDFS.range, MFG.StorageUnit) in graph
    assert (PROCESS.movementToStorage, RDFS.domain, PROCESS.MaterialMovement) in graph
    assert (PROCESS.movementToStorage, RDFS.range, MFG.StorageUnit) in graph
    assert (PROCESS.usesTransferRoute, RDFS.domain, PROCESS.MaterialMovement) in graph
    assert (PROCESS.usesTransferRoute, RDFS.range, PROCESS.TransferRoute) in graph
    assert (PROCESS.movementCarriesLot, RDFS.range, MFG.MaterialLot) in graph
    assert (PROCESS.movementForSchedule, RDFS.range, MFG.OperationsSchedule) in graph
    assert (PROCESS.routeFromStorage, RDFS.range, MFG.StorageUnit) in graph
    assert (PROCESS.routeToStorage, RDFS.range, MFG.StorageUnit) in graph


def test_phase3_version_floor_and_manufacturing_dependency_are_preserved():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    modules = {item["id"]: item for item in catalogue["modules"]}

    process_module = modules["process_industry"]
    assert _version_tuple(process_module["version"]) >= (0, 1, 4)
    assert process_module["tier"] == "domain"

    dependencies = {item["module"] for item in process_module["depends_on"]}
    assert {"core", "industrial", "asset", "kinetic", "manufacturing"}.issubset(dependencies)

    manufacturing = modules["manufacturing"]
    manufacturing_dependencies = {item["module"] for item in manufacturing["depends_on"]}
    assert "process_industry" not in manufacturing_dependencies
