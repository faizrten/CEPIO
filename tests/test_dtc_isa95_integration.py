from pathlib import Path

import yaml
from packaging.version import Version
from rdflib import OWL, RDF, URIRef

from cepio.modules import ModuleCatalogue
from cepio.registry import TypeRegistry

ROOT = Path(__file__).parents[1]
MAPPING = ROOT / "mappings" / "dtc_isa95_to_cepio.yaml"


def _contract() -> dict:
    return yaml.safe_load(MAPPING.read_text(encoding="utf-8"))


def test_manufacturing_module_is_registered_and_parseable() -> None:
    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    module = catalogue.modules["manufacturing"]
    assert module.namespace == "https://cepio.org/ontology/manufacturing#"
    assert Version(module.version) >= Version("0.1.0")
    assert module.tier == "domain"

    registry = TypeRegistry.from_ontology_dir(ROOT / "ontologies")
    for concept in [
        "HierarchyScope",
        "MaterialLot",
        "OperationsDefinition",
        "OperationsCapability",
        "OperationsRequest",
        "OperationsEvent",
        "JobOrder",
        "WorkPerformance",
        "WorkflowSpecification",
        "ResourceRelationshipNetwork",
    ]:
        assert concept in registry.object_types


def test_dtc_source_is_pinned_and_attributed() -> None:
    contract = _contract()
    source = contract["source"]
    assert source["repository"] == "https://github.com/digitaltwinconsortium/ManufacturingOntologies"
    assert source["commit"] == "f6b45fc83c922177fa7590c530339c4876b677c6"
    assert source["license"] == "CC-BY-4.0"
    assert source["dtdl_root"] == "Ontologies/ISA95"
    assert source["wot_root"] == "Ontologies/ISA95-WoT"
    assert contract["federation_policy"]["vendor_source_files"] is False
    assert contract["federation_policy"]["property_object_rule"]["disposition"] == "canonical_property_contract"


def test_dtc_mapping_source_ids_are_unique_and_targets_exist() -> None:
    contract = _contract()
    mappings = contract["mappings"]
    source_ids = [row["source_id"] for row in mappings]
    assert len(source_ids) == len(set(source_ids))
    assert all(source_id.startswith("dtmi:digitaltwins:isa95:") for source_id in source_ids)

    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    graph = catalogue.graph(ROOT)
    missing = [
        row["canonical_iri"]
        for row in mappings
        if (URIRef(row["canonical_iri"]), RDF.type, OWL.Class) not in graph
    ]
    assert missing == []


def test_shared_isa95_concepts_converge_on_existing_cepio_types() -> None:
    mappings = {row["source_concept"]: row for row in _contract()["mappings"]}
    assert mappings["Equipment"]["canonical_iri"] == "https://cepio.org/ontology/industrial#Equipment"
    assert mappings["PhysicalAsset"]["canonical_iri"] == "https://cepio.org/ontology/core#PhysicalAsset"
    assert mappings["Person"]["canonical_iri"] == "https://cepio.org/ontology/core#Person"
    assert mappings["MaterialRequirement"]["canonical_iri"] == "https://cepio.org/ontology/supply#MaterialRequirement"


def test_manufacturing_specific_isa95_concepts_use_manufacturing_namespace() -> None:
    mappings = {row["source_concept"]: row for row in _contract()["mappings"]}
    for concept in [
        "HierarchyScope",
        "OperationsDefinition",
        "OperationsCapability",
        "OperationsSchedule",
        "OperationsRequest",
        "OperationsResponse",
        "WorkDefinition",
        "WorkRequest",
        "JobOrder",
        "WorkflowSpecification",
    ]:
        assert mappings[concept]["canonical_iri"].startswith("https://cepio.org/ontology/manufacturing#")


def test_mapping_contract_covers_part2_and_part4_families() -> None:
    families = _contract()["families"]
    assert set(families["part2"]) >= {
        "Material",
        "OperationsCapability",
        "OperationsDefinition",
        "OperationsPerformance",
        "OperationsSchedule",
        "Personnel",
        "PhysicalAssetAndEquipment",
        "ProcessSegment",
    }
    assert set(families["part4"]) >= {
        "ResourceRelationship",
        "WorkCapability",
        "WorkDefinition",
        "WorkPerformance",
        "WorkSchedule",
        "WorkflowSpecification",
    }
