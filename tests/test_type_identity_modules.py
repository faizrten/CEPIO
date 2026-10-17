from pathlib import Path

import pytest
from rdflib import Graph

from cepio.modules import ModuleCatalogue, compare_snapshots
from cepio.registry import AmbiguousTypeError, TypeRegistry

ROOT = Path(__file__).parents[1]


def _version_tuple(value: object) -> tuple[int, ...]:
    return tuple(int(part) for part in str(value).split("."))


def test_registry_uses_iri_as_canonical_identity_with_local_aliases():
    registry = TypeRegistry.from_ontology_dir(ROOT / "ontologies")
    iri = "https://cepio.org/ontology/industrial#WorkOrder"
    assert registry.resolve_type("WorkOrder") == iri
    assert registry.resolve_type(iri) == iri
    assert registry.resolve_type("industrial:WorkOrder") == iri
    assert registry.same_type("WorkOrder", iri)


def test_ambiguous_local_alias_fails_closed():
    graph = Graph()
    graph.parse(data="""
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <https://cepio.org/ontology/industrial#WorkOrder> a owl:Class .
        <https://example.org/seo#WorkOrder> a owl:Class .
    """, format="turtle")
    registry = TypeRegistry.from_graph(graph)
    with pytest.raises(AmbiguousTypeError):
        registry.resolve_type("WorkOrder")
    assert registry.resolve_type("https://example.org/seo#WorkOrder") == "https://example.org/seo#WorkOrder"


def test_module_catalogue_is_versioned_unique_and_acyclic():
    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    order = catalogue.topological_order()
    assert order.index("core") < order.index("industrial") < order.index("drilling")
    assert _version_tuple(catalogue.modules["reliability"].version) >= (0, 1, 1)
    assert len({m.namespace for m in catalogue.modules.values()}) == len(catalogue.modules)


def test_snapshot_compatibility_detects_breaking_and_additive_changes():
    old = {"modules": {"x": {"classes": ["urn:A"], "relationships": ["urn:r"], "parents": [], "domains": [], "ranges": []}}}
    new = {"modules": {"x": {"classes": ["urn:A", "urn:B"], "relationships": [], "parents": [], "domains": [], "ranges": []}}}
    result = compare_snapshots(old, new)
    assert "class added: urn:B" in result["additive"]
    assert "relationship removed: urn:r" in result["breaking"]
