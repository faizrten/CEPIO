from __future__ import annotations

import json
import time
import tracemalloc

import pytest
from pydantic import ValidationError

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.policy import RolePolicyEngine
from cepio.relationship_query import (
    HostRelationshipReader,
    RelationshipPageQuery,
    RelationshipQueryUnavailable,
    RelationshipVisibility,
    SQLiteRelationshipPageAdapter,
)
from cepio.repositories import InMemoryRepository, SQLiteRepository
from cepio.runtime import AuthorizationError


@pytest.fixture
def world(tmp_path):
    runtime = build_runtime(
        sqlite_path=tmp_path / "query.db", validate_types=False, validate_properties=False
    )
    runtime.policy_engine = RolePolicyEngine(
        {
            "reader": {
                "read_types": ["Asset", "Order"],
                "read_scopes": ["shared"],
                "read_properties": {"Asset": ["status"], "Order": ["status"]},
            },
        }
    )
    repo = runtime.object_repository
    adapter = SQLiteRelationshipPageAdapter(repo)
    state = {
        "identity": ExecutionContext(
            actor_id="host-user", tenant_id="tenant-a", actor_roles=frozenset({"reader"})
        ),
        "grants": RelationshipVisibility(
            relationship_types=frozenset({"hasOrder"}),
            classifications=frozenset({"ordinary"}),
            source_uses=frozenset({"inspect"}),
            policy_version="v1",
        ),
    }
    service = CEPIOApplicationService(runtime)
    reader = HostRelationshipReader(
        service, adapter, lambda: state["identity"], lambda _: state["grants"]
    )

    def obj(identifier, *, tenant="tenant-a", kind="Order", scope="shared", bind=True):
        stored = repo.upsert_object(
            OntologyObject(
                id=identifier,
                type=kind,
                name=identifier,
                properties={"status": "candidate", "secret": "hidden", "sharingScope": scope},
            )
        )
        if bind:
            adapter.bind_object(identifier, tenant_id=tenant)
        return stored

    def rel(
        identifier,
        source="asset",
        target="order",
        *,
        tenant="tenant-a",
        classification="ordinary",
        use="inspect",
        kind="hasOrder",
        bind=True,
        source_type=None,
        target_type=None,
    ):
        stored = repo.add_relationship(
            Relationship(
                id=identifier,
                type=kind,
                source=ObjectRef(id=source, type=source_type or repo.get_object(source).type),
                target=ObjectRef(id=target, type=target_type or repo.get_object(target).type),
                properties={"secret_link_property": "never returned"},
            )
        )
        if bind:
            adapter.bind_relationship(
                identifier, tenant_id=tenant, classification=classification, source_use=use
            )
        return stored

    obj("asset", kind="Asset")
    obj("order")
    yield runtime, repo, adapter, reader, state, obj, rel
    repo.close()


def test_positive_page_projection_inverse_and_opaque_cursor(world):
    _, repo, _, reader, _, obj, rel = world
    for n in range(3):
        obj(f"order-{n}")
        rel(f"r-{n}", target=f"order-{n}")
    repo.get_relationships = lambda *a, **k: pytest.fail("unbounded relationship read")
    repo.list_objects = lambda *a, **k: pytest.fail("unbounded object read")
    first = reader.read(RelationshipPageQuery(asset_id="asset", limit=2))
    assert [x.related.id for x in first.links] == ["order-0", "order-1"]
    assert first.subject.properties == {"status": "candidate"}
    assert all(x.properties == {"status": "candidate"} for x in first.related_objects)
    assert first.next_cursor and "order" not in first.next_cursor
    second = reader.read(RelationshipPageQuery(asset_id="asset", limit=2, cursor=first.next_cursor))
    assert [x.related.id for x in second.links] == ["order-2"]
    assert second.next_cursor is None
    incoming = reader.read(RelationshipPageQuery(asset_id="order-0", direction="in"))
    assert incoming.links[0].related.id == "asset"
    assert incoming.links[0].direction == "in"
    assert "secret" not in first.model_dump_json()


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "tenant-b"),
        ("actor_id", "admin"),
        ("actor_roles", ["admin"]),
        ("limit", 0),
        ("limit", 51),
        ("limit", True),
        ("direction", "both"),
        ("cursor", "x" * 129),
    ],
)
def test_payload_cannot_declare_identity_or_invalid_bounds(field, value):
    with pytest.raises(ValidationError):
        RelationshipPageQuery.model_validate({"asset_id": "asset", field: value})


@pytest.mark.parametrize(
    "reason",
    [
        "tenant",
        "endpoint_tenant",
        "classification",
        "use",
        "type",
        "hidden",
        "unbound",
        "unbound_object",
        "wrong_type",
        "deleted",
    ],
)
def test_denied_neighbors_do_not_appear_in_page_or_cursor(world, reason):
    _, repo, adapter, reader, _, obj, rel = world
    if reason == "endpoint_tenant":
        adapter.bind_object("order", tenant_id="tenant-b")
    if reason == "hidden":
        obj("order", scope="restricted")
    if reason == "unbound_object":
        obj("order", bind=False)
    kwargs = {"tenant": "tenant-b"} if reason == "tenant" else {}
    kwargs.update({"classification": "restricted"} if reason == "classification" else {})
    kwargs.update({"use": "forbidden"} if reason == "use" else {})
    kwargs.update({"kind": "secretRelation"} if reason == "type" else {})
    kwargs.update({"bind": False} if reason == "unbound" else {})
    kwargs.update({"target_type": "Retyped"} if reason == "wrong_type" else {})
    rel("denied", **kwargs)
    if reason == "deleted":
        repo._conn.execute("DELETE FROM object_tenancy WHERE id='order'")
        repo._conn.commit()
    page = reader.read(RelationshipPageQuery(asset_id="asset"))
    assert page.links == [] and page.related_objects == [] and page.next_cursor is None
    assert "order" not in page.model_dump_json()


@pytest.mark.parametrize(
    "drift",
    [
        "actor",
        "roles",
        "tenant",
        "source",
        "policy",
        "object",
        "relation",
        "binding",
        "asset",
        "limit",
        "tamper",
        "expired",
    ],
)
def test_cursor_rejects_tampering_and_every_authority_or_snapshot_drift(world, drift, monkeypatch):
    runtime, repo, adapter, reader, state, obj, rel = world
    rel("a")
    rel("b")
    cursor = reader.read(RelationshipPageQuery(asset_id="asset", limit=1)).next_cursor
    query = {"asset_id": "asset", "limit": 1, "cursor": cursor}
    if drift in {"actor", "roles", "tenant"}:
        update = {
            "actor": {"actor_id": "other"},
            "roles": {"actor_roles": frozenset({"other"})},
            "tenant": {"tenant_id": "tenant-b"},
        }[drift]
        state["identity"] = state["identity"].model_copy(update=update)
    elif drift == "source":
        state["grants"] = state["grants"].model_copy(update={"source_uses": frozenset()})
    elif drift == "policy":
        runtime.policy_engine.policies["reader"]["read_properties"]["Order"] = []
    elif drift == "object":
        obj("order", kind="Retyped")
    elif drift == "relation":
        repo._conn.execute("UPDATE relationships SET type='other' WHERE id='a'")
        repo._conn.commit()
    elif drift == "binding":
        adapter.bind_relationship(
            "a", tenant_id="tenant-a", classification="ordinary", source_use="new"
        )
    elif drift == "asset":
        query["asset_id"] = "order"
    elif drift == "limit":
        query["limit"] = 2
    elif drift == "tamper":
        query["cursor"] += "x"
    elif drift == "expired":
        monkeypatch.setattr(time, "monotonic", lambda: 10**12)
    with pytest.raises(RelationshipQueryUnavailable, match="Invalid or stale"):
        reader.read(RelationshipPageQuery(**query))


def test_missing_host_identity_subject_and_unsupported_policy_fail_closed(world):
    runtime, _, adapter, reader, state, _, _ = world
    state["identity"] = ExecutionContext(actor_id="caller")
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))
    state["identity"] = ExecutionContext(actor_id="user", tenant_id="tenant-b")
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))
    state["identity"] = ExecutionContext(actor_id="user", tenant_id="tenant-a")
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="missing"))
    runtime.policy_engine = object()
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset"))
    with pytest.raises(RelationshipQueryUnavailable):
        SQLiteRelationshipPageAdapter(InMemoryRepository())
    with pytest.raises(RelationshipQueryUnavailable):
        HostRelationshipReader(
            CEPIOApplicationService(build_runtime()), adapter, lambda: None, lambda _: None
        )


def test_host_binding_validation_and_legacy_metadata_not_authority(world):
    _, repo, adapter, reader, _, obj, rel = world
    with pytest.raises(ValueError):
        adapter.bind_object("asset", tenant_id="")
    with pytest.raises(ValueError):
        adapter.bind_object("missing", tenant_id="tenant-a")
    with pytest.raises(ValueError):
        adapter.bind_relationship(
            "missing", tenant_id="tenant-a", classification="", source_use="inspect"
        )
    with pytest.raises(ValueError):
        adapter.bind_relationship(
            "missing", tenant_id="tenant-a", classification="ordinary", source_use="inspect"
        )
    rel("legacy", bind=False)
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []
    # Object property declarations do not establish a tenancy binding.
    stored = obj("asset", kind="Asset", bind=False)
    stored.properties["tenant_id"] = "tenant-a"
    repo.upsert_object(stored)
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))


def test_thousands_of_links_bounded_memory_vm_and_no_full_graph_materialization(
    world, record_property
):
    _, repo, adapter, reader, _, _, rel = world
    template = rel("r-00000", classification="restricted")
    # Bulk seed the same persisted rows/bindings for query qualification; importer
    # validation is exercised separately. Avoid thousands of disk fsyncs in setup.
    relations, bindings = [], []
    for n in range(1, 3000):
        identifier = f"r-{n:05d}"
        payload = template.model_copy(update={"id": identifier}).model_dump_json()
        relations.append((identifier, template.type, "asset", "order", payload))
        bindings.append(
            (identifier, payload, "tenant-a", "restricted" if n < 600 else "ordinary", "inspect")
        )
    repo._conn.executemany(
        "INSERT INTO relationships(id,type,source_id,target_id,payload) VALUES(?,?,?,?,?)",
        relations,
    )
    repo._conn.executemany(
        "INSERT INTO relationship_visibility(id,payload,tenant,classification,source_use) VALUES(?,?,?,?,?)",
        bindings,
    )
    repo._conn.commit()
    repo.get_relationships = lambda *a, **k: pytest.fail("unbounded relationship read")
    repo.list_objects = lambda *a, **k: pytest.fail("unbounded object read")
    tracemalloc.start()
    started = time.perf_counter()
    page = reader.read(RelationshipPageQuery(asset_id="asset", limit=5))
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(page.links) == 5 and page.next_cursor
    assert adapter.last_vm_steps < 200_000
    assert peak < 1_000_000
    # Broad machine-independent regression ceiling; exact measurements retained.
    assert elapsed < 5
    evidence = {
        "relationships": 3000,
        "hidden_before_page": 600,
        "page_limit": 5,
        "materialized_max": 6,
        "sqlite_vm_steps": adapter.last_vm_steps,
        "peak_bytes": peak,
        "elapsed_seconds": elapsed,
    }
    record_property("load_baseline", json.dumps(evidence))
    print(json.dumps(evidence, sort_keys=True))


def test_work_budget_fails_closed_and_clears_sqlite_handler(world, monkeypatch):
    _, repo, adapter, reader, _, _, rel = world
    rel("r")
    import cepio.relationship_query as module

    monkeypatch.setattr(
        module,
        "_PAGE_SQL",
        "WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT * FROM n",
    )
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset"))
    assert adapter.last_vm_steps == 200_000
    assert repo.get_object("asset") is not None


def test_empty_grants_default_deny_and_scope_arrays(world):
    runtime, _, _, reader, state, obj, rel = world
    obj("order", scope=["restricted", "shared"])
    rel("a")
    assert len(reader.read(RelationshipPageQuery(asset_id="asset")).links) == 1
    state["grants"] = state["grants"].model_copy(update={"classifications": frozenset()})
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []
    runtime.policy_engine = RolePolicyEngine()
    state["grants"] = RelationshipVisibility(
        relationship_types=frozenset({"hasOrder"}),
        classifications=frozenset({"ordinary"}),
        source_uses=frozenset({"inspect"}),
        policy_version="v2",
    )
    # Empty legacy policy does not make sharingScope readable without scope grants.
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))


def test_delete_recreate_same_ids_never_inherits_tenant_or_relationship_grants(world):
    _, repo, adapter, reader, _, obj, rel = world
    relationship = rel("r")
    repo._conn.execute("DELETE FROM relationships WHERE id='r'")
    repo._conn.commit()
    # Exercise base-table lifecycle without rewriting append-only temporal history.
    SQLiteRepository.add_relationship(repo, relationship)
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []
    adapter.bind_relationship(
        "r", tenant_id="tenant-a", classification="ordinary", source_use="inspect"
    )
    assert len(reader.read(RelationshipPageQuery(asset_id="asset")).links) == 1
    repo._conn.execute("DELETE FROM relationships WHERE id='r'")
    repo._conn.execute("DELETE FROM objects WHERE id='order'")
    repo._conn.commit()
    recreated = SQLiteRepository.upsert_object(
        repo, OntologyObject(id="order", type="Order", name="order")
    )
    assert recreated.version == 1
    SQLiteRepository.add_relationship(repo, relationship)
    adapter.bind_relationship(
        "r", tenant_id="tenant-a", classification="ordinary", source_use="inspect"
    )
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []


def test_registry_inheritance_and_registry_drift_invalidate_cursor(world):
    from cepio.registry import TypeRegistry

    runtime, _, _, reader, _, _, rel = world
    registry = TypeRegistry(
        object_type_ids={"Asset", "Order", "Thing"},
        parents={"Asset": {"Thing"}, "Order": {"Thing"}},
    )
    runtime.policy_engine = RolePolicyEngine(
        {
            "reader": {
                "read_types": ["Thing"],
                "read_scopes": ["shared"],
                "read_properties": {"Thing": ["status"]},
            }
        },
        type_registry=registry,
    )
    rel("a")
    rel("b")
    first = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    assert first.related_objects[0].properties == {"status": "candidate"}
    registry.parents["Order"] = set()
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1, cursor=first.next_cursor))


def test_unscoped_objects_and_explicit_wildcard_policy(world):
    runtime, repo, adapter, reader, _, _, rel = world
    runtime.policy_engine = RolePolicyEngine(
        {"reader": {"read_types": ["*"], "read_scopes": ["*"]}}
    )
    rel("a")
    assert len(reader.read(RelationshipPageQuery(asset_id="asset")).links) == 1
    for identifier in ("asset", "order"):
        obj = repo.get_object(identifier)
        del obj.properties["sharingScope"]
        repo.upsert_object(obj)
        adapter.bind_object(identifier, tenant_id="tenant-a")
    runtime.policy_engine = RolePolicyEngine()
    assert len(reader.read(RelationshipPageQuery(asset_id="asset")).links) == 1


def test_cursor_cache_is_bounded_and_eviction_fails_closed(world):
    _, _, _, reader, _, _, rel = world
    rel("a")
    rel("b")
    first = reader.read(RelationshipPageQuery(asset_id="asset", limit=1)).next_cursor
    for _ in range(1024):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    assert len(reader._cursors) == 1024
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1, cursor=first))


@pytest.mark.parametrize(
    "path,value",
    [("id", "forged"), ("type", "forbidden"), ("source.id", "forged"), ("target.id", "forged")],
)
def test_mismatched_persisted_relationship_identity_is_never_visible(world, path, value):
    _, repo, adapter, reader, _, _, rel = world
    relationship = rel("r").model_dump(mode="json")
    if "." in path:
        key, field = path.split(".")
        relationship[key][field] = value
    else:
        relationship[path] = value
    repo._conn.execute(
        "UPDATE relationships SET payload=? WHERE id='r'", (json.dumps(relationship),)
    )
    repo._conn.commit()
    adapter.bind_relationship(
        "r", tenant_id="tenant-a", classification="ordinary", source_use="inspect"
    )
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []


def test_defense_in_depth_rechecks_policy_after_adapter_read(world, monkeypatch):
    _, _, adapter, reader, _, obj, _ = world
    restricted = obj("hidden", scope="restricted")
    monkeypatch.setattr(
        adapter,
        "page",
        lambda *a: [{"id": "bad", "type": "hasOrder", "neighbor": restricted.model_dump_json()}],
    )
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset"))
