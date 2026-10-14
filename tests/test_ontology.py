from pathlib import Path

from rdflib import Graph

from cepio.registry import TypeRegistry

ROOT = Path(__file__).parents[1]


def test_all_turtle_modules_parse():
    graph = Graph()
    for path in (ROOT / "ontologies").glob("*.ttl"):
        graph.parse(path, format="turtle")
    assert len(graph) > 30


def test_registry_contains_key_types():
    registry = TypeRegistry.from_ontology_dir(ROOT / "ontologies")
    assert "Asset" in registry.object_types
    assert "Compressor" in registry.object_types
    assert "ActionType" in registry.object_types
    assert "contains" in registry.relationship_types
