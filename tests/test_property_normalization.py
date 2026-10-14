from pathlib import Path
import csv
import json

from rdflib import Graph, OWL, RDF, URIRef

from cepio.property_registry import PropertyRegistry

ROOT = Path(__file__).parents[1]


def _mapping_examples() -> list[dict[str, str]]:
    with (ROOT / "mappings/property_mapping_examples.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_property_mapping_manifest_records_complete_reference_coverage():
    manifest = json.loads((ROOT / "mappings/property_mapping_manifest.json").read_text())
    assert manifest["generated_rows"]["seo_property_to_cepio.csv"] == 441
    assert manifest["generated_rows"]["ad_property_to_cepio.csv"] == 526
    assert len(manifest["artifacts"]["mappings/seo_property_to_cepio.csv"]["sha256"]) == 64
    assert len(manifest["artifacts"]["mappings/ad_property_to_cepio.csv"]["sha256"]) == 64


def test_representative_mapping_examples_cover_structural_semantic_and_observation_roles():
    examples = _mapping_examples()
    assert {"canonical-property", "relationship-key", "observation-value", "profile-property"}.issubset(
        {row["mapping_kind"] for row in examples}
    )
    equipment_fk = next(
        row for row in examples
        if row["source_entity"] == "WorkOrder" and row["source_property"] == "EquipmentId"
    )
    assert equipment_fk["mapping_kind"] == "relationship-key"
    assert equipment_fk["canonical_property"] == ""
    temp = next(
        row for row in examples
        if row["source_entity"] == "Site" and row["source_property"] == "MaxTempC"
    )
    assert temp["mapping_kind"] == "observation-value"
    assert temp["observation_metric"] == "MaxTempC"


def test_every_example_canonical_mapping_resolves_to_property_registry():
    registry = PropertyRegistry.from_yaml(ROOT / "mappings/canonical_properties.yaml")
    for row in _mapping_examples():
        if row["mapping_kind"] in {"canonical-property", "observation-value", "observation-timestamp"}:
            definition = registry.resolve(row["canonical_property"])
            assert row["canonical_property_iri"] == definition.iri
            assert row["canonical_datatype"] == definition.datatype


def test_canonical_property_iris_are_declared_as_rdf_datatype_properties():
    registry = PropertyRegistry.from_yaml(ROOT / "mappings/canonical_properties.yaml")
    graph = Graph()
    for path in (ROOT / "ontologies").glob("*.ttl"):
        graph.parse(path, format="turtle")
    missing = [
        p.iri
        for p in registry.properties.values()
        if (URIRef(p.iri), RDF.type, OWL.DatatypeProperty) not in graph
    ]
    assert missing == []
