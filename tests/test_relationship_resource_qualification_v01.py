"""Synthetic resource pressure; no endpoint or native-memory guarantee."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import sqlite3
import time

import pytest

from cepio.application_contract import CEPIOApplicationService
from cepio.relationship_qualification import (
    RelationshipQualificationBoundary,
    RelationshipQualificationUnavailable,
)
from cepio.relationship_query import RelationshipPageQuery, RelationshipQueryUnavailable
from test_relationship_query_v01 import world as world
from test_relationship_source_access_v01 import sources as sources


@pytest.fixture
def bounded(sources, world):
    _, adapter, _, state, _, _ = sources
    return RelationshipQualificationBoundary(
        CEPIOApplicationService(world[0]),
        adapter,
        lambda: state["identity"],
        lambda _: state["grants"],
        lambda _: state["access"],
    )


def test_connection_limits_restored_after_success_and_failure(bounded, sources):
    repo = sources[0]
    before = repo._conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
    busy = repo._conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert bounded.read({"asset_id": "asset"}).links
    with pytest.raises(RelationshipQualificationUnavailable):
        bounded.read({"asset_id": "missing"})
    assert repo._conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) == before
    assert repo._conn.execute("PRAGMA busy_timeout").fetchone()[0] == busy
    assert sources[1]._qualification_deadline is None
    assert not repo._conn.in_transaction


def test_lock_contention_is_bounded_and_recovers(bounded, sources):
    entered, release = Event(), Event()

    def hold():
        with sources[0]._lock:
            entered.set()
            assert release.wait(5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(hold)
        assert entered.wait(5)
        started = time.monotonic()
        try:
            with pytest.raises(RelationshipQualificationUnavailable):
                bounded.read({"asset_id": "asset"})
            assert time.monotonic() - started < 2
        finally:
            release.set()
        future.result()
    assert bounded.read({"asset_id": "asset"}).links


@pytest.mark.parametrize("identifier", ["asset", "order"])
def test_oversized_stored_objects_fail_before_object_parsing(bounded, sources, identifier):
    repo, adapter, _, _, _, _ = sources
    obj = repo.get_object(identifier)
    obj.properties["secret"] = "x" * 100_000
    repo.upsert_object(obj)
    adapter.bind_object(identifier, tenant_id="tenant-a")
    adapter.bind_object_sources(
        identifier, frozenset({"source-asset" if identifier == "asset" else "source-order"})
    )
    with pytest.raises(RelationshipQualificationUnavailable) as error:
        bounded.read({"asset_id": "asset"})
    assert str(error.value) == "Relationship query unavailable"
    assert not repo._conn.in_transaction
    # The shared repository's original limit and unrelated host-local use survive.
    assert len(repo.get_object(identifier).properties["secret"]) == 100_000


def test_existing_stricter_connection_limit_is_preserved(sources):
    repo, adapter, *_ = sources
    original = repo._conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 32_768)
    try:
        with adapter.qualification_budget():
            assert repo._conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) == 32_768
        assert repo._conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) == 32_768
    finally:
        repo._conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, original)


def test_elapsed_budget_discards_late_result_and_restores(bounded, sources, monkeypatch):
    adapter = sources[1]
    original = bounded._reader.read

    def late(query):
        page = original(query)
        adapter._qualification_deadline = time.monotonic() - 1
        return page

    monkeypatch.setattr(bounded._reader, "read", late)
    with pytest.raises(RelationshipQualificationUnavailable):
        bounded.read({"asset_id": "asset"})
    assert adapter._qualification_deadline is None


def test_deadline_interrupts_vm_and_removes_progress_handler(sources):
    repo, adapter, reader, *_ = sources
    with adapter.qualification_budget():
        adapter._qualification_deadline = time.monotonic() - 1
        with pytest.raises(RelationshipQueryUnavailable):
            reader.read(RelationshipPageQuery(asset_id="asset"))
        # Restore for context exit; the page handler was removed even on abort.
        adapter._qualification_deadline = time.monotonic() + 1
        assert repo._conn.execute("SELECT count(*) FROM objects").fetchone()[0] == 2
    assert reader.read(RelationshipPageQuery(asset_id="asset")).links


def test_response_utf8_budget_rejects_aggregate_and_releases_slots(bounded, sources):
    repo, adapter, _, _, _, rel = sources
    obj = repo.get_object("order")
    obj.properties["status"] = "\u00e9" * 15_000
    repo.upsert_object(obj)
    adapter.bind_object("order", tenant_id="tenant-a")
    adapter.bind_object_sources("order", frozenset({"source-order"}))
    for index in range(10):
        identifier = f"extra-{index}"
        rel(identifier)
        adapter.bind_relationship_sources(identifier, frozenset({"source-edge"}))
    with pytest.raises(RelationshipQualificationUnavailable):
        bounded.read({"asset_id": "asset", "limit": 20})
    assert len(bounded.read({"asset_id": "asset", "limit": 1}).links) == 1


@pytest.mark.parametrize("denied_count", [0, 600, 2000])
def test_denied_fanout_resource_envelope(bounded, sources, denied_count, record_property):
    """Measure residual leakage, never claim constant-time from padded errors."""
    import json
    import tracemalloc

    _, adapter, _, _, _, rel = sources
    for index in range(denied_count):
        identifier = f"denied-{index:05d}"
        rel(identifier)
        adapter.bind_relationship_sources(identifier, frozenset({"denied-origin"}))
    tracemalloc.start()
    started = time.perf_counter()
    try:
        page = bounded.read({"asset_id": "asset", "limit": 1})
        outcome = "page"
        assert len(page.links) == 1
    except RelationshipQualificationUnavailable:
        outcome = "unavailable"
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert adapter.last_vm_steps <= 200_000
    assert peak < 1_000_000
    # Wall-clock observation has generous scheduling tolerance; the deterministic
    # guards are separately tested. This is not a production latency guarantee.
    assert elapsed < 5
    if denied_count == 0:
        assert outcome == "page"
    if denied_count == 2000:
        assert outcome == "unavailable"
    evidence = dict(
        denied_count=denied_count,
        outcome=outcome,
        vm_steps=adapter.last_vm_steps,
        elapsed_seconds=elapsed,
        python_peak_bytes=peak,
    )
    record_property("denied_fanout_envelope", json.dumps(evidence))
    print(json.dumps(evidence, sort_keys=True))


def test_external_database_lock_is_bounded_and_recovers(bounded, sources):
    repo = sources[0]
    blocker = sqlite3.connect(repo.path)
    try:
        blocker.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        with pytest.raises(RelationshipQualificationUnavailable):
            bounded.read({"asset_id": "asset"})
        assert time.monotonic() - started < 2
    finally:
        blocker.rollback()
        blocker.close()
    assert bounded.read({"asset_id": "asset"}).links
