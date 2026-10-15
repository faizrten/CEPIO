from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import cepio.api as api_module
from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.query import ObjectQuery, PropertyPredicate, QueryOperator, RelationshipPredicate, SortField


def _runtime(tmp_path, sqlite: bool):
    return build_runtime(sqlite_path=tmp_path / "query.db") if sqlite else build_runtime()


def _seed(runtime):
    unit = runtime.upsert_object(
        OntologyObject(id="HCU-01", type="Hydrocracker", name="Hydrocracking Unit", properties={"site": "Jubail"})
    )
    k201 = runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="Recycle Gas Compressor K-201",
            properties={"criticality": "high", "riskScore": 0.82},
        )
    )
    k202 = runtime.upsert_object(
        OntologyObject(
            id="K-202",
            type="Compressor",
            name="Recycle Gas Compressor K-202",
            properties={"criticality": "medium", "riskScore": 0.31},
        )
    )
    runtime.add_relationship(
        Relationship(
            id="REL-HCU-K201",
            type="contains",
            source=ObjectRef(id=unit.id, type=unit.type),
            target=ObjectRef(id=k201.id, type=k201.type),
        )
    )
    return unit, k201, k202


@pytest.mark.parametrize("sqlite", [False, True])
def test_query_by_type_property_relationship_sort_and_page(tmp_path, sqlite):
    runtime = _runtime(tmp_path, sqlite)
    _seed(runtime)

    high = runtime.query_objects(
        ObjectQuery(
            object_type="Compressor",
            predicates=[PropertyPredicate(property="criticality", operator=QueryOperator.eq, value="high")],
        )
    )
    assert high.total == 1
    assert [item.id for item in high.items] == ["K-201"]

    connected = runtime.query_objects(
        ObjectQuery(
            object_type="Compressor",
            relationships=[
                RelationshipPredicate(
                    relationship_type="contains",
                    direction="in",
                    other_id="HCU-01",
                    other_type="Hydrocracker",
                )
            ],
        )
    )
    assert [item.id for item in connected.items] == ["K-201"]

    paged = runtime.query_objects(
        ObjectQuery(
            object_type="Compressor",
            sort=[SortField(field="riskScore", direction="desc")],
            offset=0,
            limit=1,
        )
    )
    assert paged.total == 2
    assert [item.id for item in paged.items] == ["K-201"]


@pytest.mark.parametrize("sqlite", [False, True])
def test_transaction_time_query_reconstructs_prior_object_state(tmp_path, sqlite):
    runtime = _runtime(tmp_path, sqlite)
    _, first, _ = _seed(runtime)
    first_tx = first.updated_at

    current = runtime.get_object("K-201")
    changed = current.model_copy(update={"properties": {**current.properties, "criticality": "low"}})
    runtime.upsert_object(changed, expected_version=current.version)

    old_state = runtime.query_objects(
        ObjectQuery(
            object_type="Compressor",
            predicates=[PropertyPredicate(property="criticality", value="high")],
            as_of_transaction=first_tx,
        )
    )
    assert [item.id for item in old_state.items] == ["K-201"]
    assert old_state.items[0].properties["criticality"] == "high"

    current_state = runtime.query_objects(
        ObjectQuery(
            object_type="Compressor",
            predicates=[PropertyPredicate(property="criticality", value="high")],
        )
    )
    assert "K-201" not in {item.id for item in current_state.items}


@pytest.mark.parametrize("sqlite", [False, True])
def test_valid_time_query_applies_relationship_validity(tmp_path, sqlite):
    runtime = _runtime(tmp_path, sqlite)
    unit = runtime.upsert_object(OntologyObject(id="HCU-T", type="Hydrocracker", name="Temporal HCU"))
    compressor = runtime.upsert_object(OntologyObject(id="K-T", type="Compressor", name="Temporal Compressor"))
    valid_at = max(unit.updated_at, compressor.updated_at) + timedelta(seconds=1)

    runtime.add_relationship(
        Relationship(
            id="REL-TEMPORAL",
            type="contains",
            source=ObjectRef(id=unit.id, type=unit.type),
            target=ObjectRef(id=compressor.id, type=compressor.type),
            valid_from=valid_at - timedelta(minutes=5),
            valid_to=valid_at + timedelta(minutes=5),
        )
    )

    query = ObjectQuery(
        object_type="Compressor",
        valid_at=valid_at,
        relationships=[RelationshipPredicate(relationship_type="contains", direction="in", other_id=unit.id)],
    )
    assert [item.id for item in runtime.query_objects(query).items] == [compressor.id]

    expired = query.model_copy(update={"valid_at": valid_at + timedelta(minutes=10)})
    assert runtime.query_objects(expired).items == []


def test_query_api_accepts_structured_contract(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")
    api_module.runtime = build_runtime()
    api_module.runtime.upsert_object(
        OntologyObject(id="K-API-Q", type="Compressor", name="Query API Compressor", properties={"criticality": "high"})
    )
    client = TestClient(api_module.app)

    response = client.post(
        "/query/objects",
        headers={
            "X-CEPIO-Dev-Actor": "query-test",
            "X-CEPIO-Dev-Roles": "maintenance_engineer",
        },
        json={
            "object_type": "Compressor",
            "predicates": [{"property": "criticality", "operator": "eq", "value": "high"}],
            "limit": 10,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == "K-API-Q"
