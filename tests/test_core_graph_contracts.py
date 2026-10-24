"""Domain-neutral graph/repository contracts independent of industrial corpora."""

from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.query import ObjectQuery, QueryEngine, SortField
from cepio.repositories import InMemoryRepository
from cepio.runtime import CEPIORuntime


def test_inverse_traversal_filters_edges_and_deduplicates_destinations():
    runtime = CEPIORuntime()
    for object_id in ("a", "b", "c", "d"):
        runtime.upsert_object(OntologyObject(id=object_id, type="Node", name=object_id))
    for edge_id, source, target, kind in (
        ("ab", "a", "b", "link"),
        ("ac", "a", "c", "link"),
        ("db", "d", "b", "other"),
    ):
        runtime.add_relationship(
            Relationship(
                id=edge_id,
                type=kind,
                source=ObjectRef(id=source, type="Node"),
                target=ObjectRef(id=target, type="Node"),
            )
        )
    assert {obj.id for obj in runtime.reverse_neighbors("b")} == {"a", "d"}
    assert [obj.id for obj in runtime.reverse_neighbors("b", "link")] == ["a"]
    assert [obj.id for obj in runtime.traverse("a", ["link", "^link"])] == ["a"]
    assert runtime.traverse("a", ["other"]) == []
    assert [obj.id for obj in runtime.traverse("a", [])] == ["a"]


def test_repository_type_filter_returns_detached_objects():
    repository = InMemoryRepository()
    repository.upsert_object(OntologyObject(id="a", type="Node", name="a"))
    repository.upsert_object(OntologyObject(id="b", type="Other", name="b"))
    selected = repository.list_objects("Node")
    assert [obj.id for obj in selected] == ["a"]
    selected[0].name = "changed"
    assert repository.get_object("a").name == "a"
    assert repository.list_objects("Absent") == []


def test_equal_sort_values_have_stable_identity_tiebreaker():
    runtime = CEPIORuntime()
    for object_id in ("c", "a", "b"):
        runtime.upsert_object(
            OntologyObject(id=object_id, type="Node", name=object_id, properties={"rank": 1})
        )
    engine = QueryEngine(runtime)
    for direction in ("asc", "desc"):
        result = engine.execute(ObjectQuery(sort=[SortField(field="rank", direction=direction)]))
        assert [obj.id for obj in result.items] == ["a", "b", "c"]
