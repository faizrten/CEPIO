from __future__ import annotations

import pytest

from cepio.graph_analytics import GraphAnalyticsEngine, GraphBackendUnavailable
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.repositories import InMemoryRepository


def build_graph_repo() -> InMemoryRepository:
    repo = InMemoryRepository()
    objects = [
        OntologyObject(id="UNIT-1", type="ProcessUnit", name="Hydrocracker"),
        OntologyObject(id="K-201", type="Compressor", name="Recycle Gas Compressor"),
        OntologyObject(id="WO-317", type="WorkOrder", name="Bearing Inspection"),
        OntologyObject(id="SP-77810", type="SparePart", name="Bearing Cartridge"),
        OntologyObject(id="SUP-1", type="Supplier", name="Bearing Supplier"),
    ]
    for obj in objects:
        repo.upsert_object(obj)

    relationships = [
        Relationship(type="contains", source=ObjectRef(id="UNIT-1", type="ProcessUnit"), target=ObjectRef(id="K-201", type="Compressor")),
        Relationship(type="hasWorkOrder", source=ObjectRef(id="K-201", type="Compressor"), target=ObjectRef(id="WO-317", type="WorkOrder")),
        Relationship(type="requiresSpare", source=ObjectRef(id="WO-317", type="WorkOrder"), target=ObjectRef(id="SP-77810", type="SparePart")),
        Relationship(type="suppliedBy", source=ObjectRef(id="SP-77810", type="SparePart"), target=ObjectRef(id="SUP-1", type="Supplier")),
        Relationship(type="dependsOn", source=ObjectRef(id="K-201", type="Compressor"), target=ObjectRef(id="SP-77810", type="SparePart")),
    ]
    for rel in relationships:
        repo.add_relationship(rel)
    return repo


def test_snapshot_preserves_cepio_object_and_relationship_context() -> None:
    engine = GraphAnalyticsEngine(build_graph_repo(), backend="networkx")
    graph = engine.snapshot()

    assert graph.number_of_nodes() == 5
    assert graph.number_of_edges() == 5
    assert graph.nodes["K-201"]["object_type"] == "Compressor"
    assert "requiresSpare" in graph["WO-317"]["SP-77810"]["relationship_types"]


def test_pagerank_and_betweenness_return_ranked_cepio_objects() -> None:
    engine = GraphAnalyticsEngine(build_graph_repo(), backend="networkx")

    pagerank = engine.centrality("pagerank", limit=3)
    betweenness = engine.centrality("betweenness", limit=5)

    assert pagerank.backend.selected == "networkx"
    assert len(pagerank.nodes) == 3
    assert pagerank.nodes == sorted(pagerank.nodes, key=lambda item: (-item.score, item.object_id))
    assert {item.object_id for item in betweenness.nodes} == {"UNIT-1", "K-201", "WO-317", "SP-77810", "SUP-1"}


def test_blast_radius_supports_direction_hops_and_relationship_filter() -> None:
    engine = GraphAnalyticsEngine(build_graph_repo(), backend="networkx")

    result = engine.blast_radius("K-201", max_hops=2, direction="out")
    assert [(item.object_id, item.hops) for item in result.nodes] == [
        ("SP-77810", 1),
        ("WO-317", 1),
        ("SUP-1", 2),
    ]

    work_only = engine.blast_radius(
        "K-201",
        max_hops=3,
        relationship_types=["hasWorkOrder", "requiresSpare"],
    )
    assert [(item.object_id, item.hops) for item in work_only.nodes] == [
        ("WO-317", 1),
        ("SP-77810", 2),
    ]


def test_communities_cover_every_object_once() -> None:
    engine = GraphAnalyticsEngine(build_graph_repo(), backend="networkx")
    result = engine.communities()

    members = [member for community in result.communities for member in community.members]
    assert sorted(members) == ["K-201", "SP-77810", "SUP-1", "UNIT-1", "WO-317"]
    assert len(members) == len(set(members))


def test_strict_cugraph_backend_fails_closed_when_not_installed() -> None:
    engine = GraphAnalyticsEngine(build_graph_repo(), backend="cugraph")
    if engine.cugraph_installed():
        pytest.skip("nx-cugraph is installed in this environment")

    with pytest.raises(GraphBackendUnavailable):
        engine.centrality("pagerank")


def test_auto_backend_is_cpu_safe_without_gpu_runtime() -> None:
    engine = GraphAnalyticsEngine(build_graph_repo(), backend="auto")
    result = engine.centrality("degree")

    assert result.backend.selected in {"networkx", "cugraph"}
    assert result.node_count == 5
    assert result.edge_count == 5
