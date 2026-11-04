"""Cursor retention accounting under synthetic pressure, without native RSS claims."""

import time

import pytest

from cepio.relationship_query import RelationshipPageQuery, RelationshipQueryUnavailable
from test_relationship_query_v01 import world as world
from test_relationship_source_access_v01 import sources as sources


def test_large_continuation_keys_cannot_fill_count_only_cache(sources):
    repo, adapter, reader, _, _, rel = sources
    repo._conn.execute("DELETE FROM relationships")
    repo._conn.commit()
    for suffix in ("a", "b"):
        identifier = "x" * 30_000 + suffix
        rel(identifier)
        adapter.bind_relationship_sources(identifier, frozenset({"source-edge"}))
    reader.configure_retention_budget()
    first = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    for _ in range(20):
        current = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
        assert reader.retained_cursor_bytes() <= 262_144
    assert len(reader._cursors) < 20
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1, cursor=first.next_cursor))
    assert (
        len(
            reader.read(
                RelationshipPageQuery(asset_id="asset", limit=1, cursor=current.next_cursor)
            ).links
        )
        == 1
    )


def test_expired_entries_reclaimed_on_next_read_without_touching_live_cursor(sources):
    _, _, reader, *_ = sources
    reader.configure_retention_budget()
    old = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    state = reader._cursors[old.next_cursor]
    reader._cursors[old.next_cursor] = (time.monotonic() - 601, *state[1:])
    live = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    assert old.next_cursor not in reader._cursors
    assert live.next_cursor in reader._cursors
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1, cursor=old.next_cursor))


def test_enabling_budget_discards_preexisting_retention_and_source_reconfiguration_clears(sources):
    _, _, reader, state, *_ = sources
    first = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    reader.configure_retention_budget()
    assert not reader._cursors and reader.retained_cursor_bytes() < 1024
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1, cursor=first.next_cursor))
    reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    reader.configure_source_access(lambda _: state["access"])
    assert not reader._cursors and reader.retained_cursor_bytes() < 1024


def test_normal_cursor_pressure_keeps_new_continuations_within_accounted_budget(sources):
    _, _, reader, *_ = sources
    reader.configure_retention_budget()
    for _ in range(450):
        page = reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
        assert reader.retained_cursor_bytes() <= 262_144
    assert page.next_cursor in reader._cursors
    assert len(reader._cursors) <= 1024
    assert (
        len(
            reader.read(
                RelationshipPageQuery(asset_id="asset", limit=1, cursor=page.next_cursor)
            ).links
        )
        == 1
    )


def test_single_oversized_cursor_fails_without_returning_unusable_continuation(sources):
    repo, adapter, reader, _, _, rel = sources
    repo._conn.execute("DELETE FROM relationships")
    repo._conn.commit()
    for suffix in ("a", "b"):
        identifier = "x" * 300_000 + suffix
        rel(identifier)
        adapter.bind_relationship_sources(identifier, frozenset({"source-edge"}))
    reader.configure_retention_budget()
    with pytest.raises(RelationshipQueryUnavailable):
        reader.read(RelationshipPageQuery(asset_id="asset", limit=1))
    assert not reader._cursors and reader.retained_cursor_bytes() <= 262_144
