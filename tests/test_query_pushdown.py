from __future__ import annotations

from fastapi.testclient import TestClient

import cepio.api as legacy_api
import cepio.public_api as public_api
from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.query import (
    ObjectQuery,
    PropertyPredicate,
    QueryOperator,
    RelationshipPredicate,
    SortField,
)


def _seed(runtime, count: int = 5):
    for index in range(count):
        runtime.upsert_object(
            OntologyObject(
                id=f"K-{index:03d}",
                type="Compressor",
                name=f"Compressor {index}",
                properties={
                    "criticality": "high" if index % 2 == 0 else "medium",
                    "riskScore": float(count - index),
                },
            )
        )


def _seed_parity(runtime):
    runtime.upsert_object(OntologyObject(id="UNIT-1", type="Hydrocracker", name="Unit 1"))
    _seed(runtime, count=6)
    for index in (0, 2, 4):
        runtime.add_relationship(
            Relationship(
                id=f"REL-{index}",
                type="contains",
                source=ObjectRef(id="UNIT-1", type="Hydrocracker"),
                target=ObjectRef(id=f"K-{index:03d}", type="Compressor"),
            )
        )


def test_sqlite_filtered_query_does_not_call_runtime_list_objects(tmp_path):
    runtime = build_runtime(sqlite_path=tmp_path / "pushdown.db")
    _seed(runtime)

    def forbidden_list(*args, **kwargs):
        raise AssertionError("SQLite pushed-down current-state query must not call runtime.list_objects()")

    runtime.list_objects = forbidden_list  # type: ignore[method-assign]
    result = runtime.query_objects(
        ObjectQuery(
            object_type="Compressor",
            predicates=[PropertyPredicate(property="criticality", operator=QueryOperator.eq, value="high")],
            sort=[SortField(field="riskScore", direction="desc")],
            limit=10,
        )
    )
    assert [item.id for item in result.items] == ["K-000", "K-002", "K-004"]
    assert result.total == 3


def test_cursor_pagination_is_opaque_and_stable_for_same_query(tmp_path):
    runtime = build_runtime(sqlite_path=tmp_path / "cursor.db")
    _seed(runtime)
    base = ObjectQuery(
        object_type="Compressor",
        sort=[SortField(field="riskScore", direction="desc")],
        limit=2,
        include_total=False,
    )

    first = runtime.query_objects(base)
    assert [item.id for item in first.items] == ["K-000", "K-001"]
    assert first.has_more is True
    assert first.next_cursor
    assert "K-001" not in first.next_cursor

    second = runtime.query_objects(base.model_copy(update={"cursor": first.next_cursor}))
    assert [item.id for item in second.items] == ["K-002", "K-003"]
    assert second.has_more is True

    third = runtime.query_objects(base.model_copy(update={"cursor": second.next_cursor}))
    assert [item.id for item in third.items] == ["K-004"]
    assert third.has_more is False
    assert third.next_cursor is None


def test_cursor_total_is_full_authorized_result_count(tmp_path):
    runtime = build_runtime(sqlite_path=tmp_path / "cursor-total.db")
    _seed(runtime)
    base = ObjectQuery(object_type="Compressor", sort=[SortField(field="id")], limit=2)
    first = runtime.query_objects(base)
    second = runtime.query_objects(base.model_copy(update={"cursor": first.next_cursor}))
    assert first.total == 5
    assert second.total == 5


def test_actor_visibility_is_applied_before_pagination(tmp_path, monkeypatch):
    runtime = build_runtime(sqlite_path=tmp_path / "auth-page.db")
    _seed(runtime)
    original = runtime.policy_engine.can_read_object

    def can_read(roles, obj):
        return obj.id != "K-001" and original(roles, obj)

    monkeypatch.setattr(runtime.policy_engine, "can_read_object", can_read)
    result = runtime.query_objects_for_actor(
        ObjectQuery(
            object_type="Compressor",
            sort=[SortField(field="riskScore", direction="desc")],
            limit=2,
        ),
        {"maintenance_engineer"},
    )
    assert [item.id for item in result.items] == ["K-000", "K-002"]
    assert result.total == 4


def test_in_memory_and_sqlite_pushdown_have_query_parity(tmp_path):
    memory = build_runtime()
    sqlite = build_runtime(sqlite_path=tmp_path / "parity.db")
    _seed_parity(memory)
    _seed_parity(sqlite)

    corpus = [
        ObjectQuery(object_type="Compressor", sort=[SortField(field="id")], limit=100),
        ObjectQuery(
            object_type="Compressor",
            predicates=[PropertyPredicate(property="criticality", operator=QueryOperator.eq, value="high")],
            sort=[SortField(field="riskScore", direction="desc")],
            limit=100,
        ),
        ObjectQuery(
            object_type="Compressor",
            predicates=[PropertyPredicate(property="riskScore", operator=QueryOperator.gte, value=3.0)],
            sort=[SortField(field="riskScore", direction="asc")],
            limit=100,
        ),
        ObjectQuery(
            object_type="Compressor",
            relationships=[
                RelationshipPredicate(
                    relationship_type="contains",
                    direction="in",
                    other_id="UNIT-1",
                    other_type="Hydrocracker",
                )
            ],
            sort=[SortField(field="id")],
            limit=100,
        ),
    ]

    for query in corpus:
        expected = memory.query_objects(query)
        actual = sqlite.query_objects(query)
        assert [item.id for item in actual.items] == [item.id for item in expected.items]
        assert actual.total == expected.total


def test_public_v1_query_budget_has_stable_error(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    legacy_api.runtime = build_runtime()
    client = TestClient(public_api.app)

    response = client.post(
        "/api/v1/query/objects",
        headers={"X-CEPIO-Dev-Actor": "query-test", "X-CEPIO-Dev-Roles": "maintenance_engineer"},
        json={"object_type": "Compressor", "limit": 201},
    )
    assert response.status_code == 429
    payload = response.json()
    assert payload["code"] == "query_budget_exceeded"
    assert payload["requestId"]
