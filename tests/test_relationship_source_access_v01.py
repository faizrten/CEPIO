"""Synthetic source-rights propagation; no source credentials or industrial IQ."""

from datetime import datetime, timedelta, timezone
import json
import time
import tracemalloc

import pytest
from pydantic import ValidationError

from cepio.application_contract import CEPIOApplicationService
from cepio.relationship_query import (
    HostRelationshipReader,
    RelationshipPageQuery,
    RelationshipQueryUnavailable,
    RelationshipSourceAccess,
)
from cepio.runtime import AuthorizationError
from test_relationship_query_v01 import world as world


@pytest.fixture
def sources(world):
    runtime, repo, adapter, _, state, obj, rel = world
    rel("r1")
    rel("r2")
    adapter.bind_object_sources("asset", frozenset({"source-asset"}))
    adapter.bind_object_sources("order", frozenset({"source-order"}))
    for identifier in ("r1", "r2"):
        adapter.bind_relationship_sources(identifier, frozenset({"source-edge"}))
    state["access"] = RelationshipSourceAccess(
        actor_id="host-user",
        tenant_id="tenant-a",
        actor_roles=frozenset({"reader"}),
        source_ids=frozenset({"source-asset", "source-order", "source-edge"}),
        rights_version="rights-v1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    reader = HostRelationshipReader(
        CEPIOApplicationService(runtime),
        adapter,
        lambda: state["identity"],
        lambda _: state["grants"],
    )
    reader.configure_source_access(lambda _: state["access"])
    return repo, adapter, reader, state, obj, rel


def test_current_source_permissions_cover_both_endpoints_and_relationship(sources):
    _, _, reader, _, _, _ = sources
    page = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    assert len(page.links) == 1 and page.next_cursor
    assert page.subject.properties == {"status": "candidate"}
    assert page.related_objects[0].properties == {"status": "candidate"}
    assert "source-" not in page.model_dump_json()
    incoming = reader.read(RelationshipPageQuery(asset_id="order", direction="in"))
    assert [link.related.id for link in incoming.links] == ["asset", "asset"]


@pytest.mark.parametrize("source", ["source-order", "source-edge"])
def test_missing_secondary_rights_hide_edges_without_count_or_cursor(sources, source):
    _, _, reader, state, _, _ = sources
    state["access"] = state["access"].model_copy(
        update={"source_ids": state["access"].source_ids - {source}}
    )
    page = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    assert page.links == [] and page.related_objects == [] and page.next_cursor is None


def test_subject_source_permission_is_mandatory(sources):
    _, _, reader, state, _, _ = sources
    state["access"] = state["access"].model_copy(update={"source_ids": frozenset()})
    with pytest.raises(AuthorizationError, match="Object is unavailable"):
        reader.read(RelationshipPageQuery(asset_id="asset"))


@pytest.mark.parametrize("part", ["subject", "neighbor", "edge"])
def test_every_contributing_source_must_be_authorized_and_bound(sources, part):
    _, adapter, reader, _, _, _ = sources
    if part == "edge":
        adapter.bind_relationship_sources("r1", frozenset({"source-edge", "restricted-parent"}))
        adapter.bind_relationship_sources("r2", frozenset({"restricted-parent"}))
    else:
        adapter.bind_object_sources(
            "asset" if part == "subject" else "order", frozenset({"restricted-parent"})
        )
    if part == "subject":
        with pytest.raises(AuthorizationError):
            reader.read(RelationshipPageQuery(asset_id="asset"))
    else:
        assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor_id", "other"),
        ("tenant_id", "tenant-b"),
        ("actor_roles", frozenset({"admin"})),
        ("expires_at", datetime(2000, 1, 1, tzinfo=timezone.utc)),
        ("expires_at", datetime(2099, 1, 1)),
    ],
)
def test_rights_snapshot_cannot_cross_identity_scope_or_expiry(sources, field, value):
    _, _, reader, state, _, _ = sources
    state["access"] = state["access"].model_copy(update={field: value})
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("purpose", "GLOBAL_LEARNING"),
        ("rights_version", ""),
        ("source_ids", frozenset(str(n) for n in range(257))),
    ],
)
def test_revalidate_frozen_adapter_results(sources, field, value):
    _, _, reader, state, _, _ = sources
    state["access"] = state["access"].model_copy(update={field: value})
    with pytest.raises(ValidationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))


@pytest.mark.parametrize("change", ["rights", "sources", "binding"])
def test_permission_or_source_binding_drift_invalidates_continuation(sources, change):
    _, adapter, reader, state, _, _ = sources
    first = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    if change == "rights":
        state["access"] = state["access"].model_copy(update={"rights_version": "revoked-v2"})
    elif change == "sources":
        state["access"] = state["access"].model_copy(
            update={"source_ids": state["access"].source_ids - {"source-edge"}}
        )
    else:
        adapter.bind_relationship_sources("r1", frozenset({"source-edge", "new-parent"}))
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1, cursor=first.next_cursor))


@pytest.mark.parametrize("entity", ["object", "edge"])
def test_unbound_legacy_sources_fail_closed(sources, entity):
    repo, _, reader, _, _, _ = sources
    if entity == "object":
        repo._conn.execute("DELETE FROM relationship_object_sources WHERE id='order'")
    else:
        repo._conn.execute("DELETE FROM relationship_edge_sources")
    repo._conn.commit()
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []


@pytest.mark.parametrize(
    "source_ids",
    [
        frozenset(),
        frozenset({""}),
        frozenset({" "}),
        frozenset({"x" * 513}),
        frozenset(range(2)),
        frozenset(str(n) for n in range(33)),
        {"mutable"},
    ],
)
def test_importer_source_bindings_are_explicit_and_bounded(sources, source_ids):
    _, adapter, _, _, _, _ = sources
    with pytest.raises(ValueError):
        adapter.bind_object_sources("asset", source_ids)
    with pytest.raises(ValueError):
        adapter.bind_relationship_sources("r1", source_ids)


def test_missing_binding_target_rejected(sources):
    _, adapter, _, _, _, _ = sources
    with pytest.raises(ValueError):
        adapter.bind_object_sources("missing", frozenset({"source"}))
    with pytest.raises(ValueError):
        adapter.bind_relationship_sources("missing", frozenset({"source"}))
    with pytest.raises(ValueError):
        sources[2].configure_source_access(None)


def test_current_clock_is_rechecked_before_releasing_page(sources, monkeypatch):
    _, _, reader, _, _, _ = sources
    # Advance the current authorization clock between admission and release.
    import cepio.relationship_query as module

    class Clock:
        calls = 0

        @classmethod
        def now(cls, tz):
            cls.calls += 1
            return datetime(2000 if cls.calls == 1 else 2100, 1, 1, tzinfo=tz)

    monkeypatch.setattr(module, "datetime", Clock)
    with pytest.raises(AuthorizationError):
        reader.read(RelationshipPageQuery(asset_id="asset"))


def test_mutation_revokes_source_bindings_even_after_tenant_rebind(sources):
    repo, adapter, reader, _, obj, _ = sources
    obj("order")
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links == []
    adapter.bind_object_sources("order", frozenset({"source-order"}))
    assert len(reader.read(RelationshipPageQuery(asset_id="asset")).links) == 2
    repo._conn.execute("UPDATE relationships SET payload=payload WHERE id='r1'")
    repo._conn.commit()
    adapter.bind_relationship(
        "r1", tenant_id="tenant-a", classification="ordinary", source_use="inspect"
    )
    assert len(reader.read(RelationshipPageQuery(asset_id="asset")).links) == 1


def test_source_denied_fanout_load_is_bounded(sources, record_property):
    repo, adapter, reader, _, _, rel = sources
    for n in range(3000):
        identifier = f"load-{n:05d}"
        rel(identifier)
        adapter.bind_relationship_sources(
            identifier, frozenset({"denied-origin" if n < 600 else "source-edge"})
        )
    repo.get_relationships = lambda *a, **k: pytest.fail("unbounded relationship scan")
    repo.list_objects = lambda *a, **k: pytest.fail("unbounded object scan")
    tracemalloc.start()
    started = time.perf_counter()
    page = reader.read(RelationshipPageQuery(asset_id="asset", limit=5))
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(page.links) == 5 and page.next_cursor
    assert adapter.last_vm_steps < 200_000 and peak < 1_000_000 and elapsed < 5
    evidence = {
        "links": 3002,
        "source_denied_before_page": 600,
        "page_limit": 5,
        "vm_steps": adapter.last_vm_steps,
        "python_peak_bytes": peak,
        "elapsed_seconds": elapsed,
    }
    record_property("source_aware_load", json.dumps(evidence))
    print(json.dumps(evidence, sort_keys=True))
