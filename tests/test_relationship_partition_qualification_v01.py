"""Offline tenant interference qualification over separate existing SQLite stores."""

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.relationship_partitions import (
    RelationshipQualificationPartition,
    RelationshipQualificationPartitions,
)
from cepio.relationship_qualification import RelationshipQualificationUnavailable
from cepio.relationship_query import RelationshipSourceAccess, SQLiteRelationshipPageAdapter
from cepio.repositories import SQLiteRepository
from test_relationship_query_v01 import world


@pytest.fixture
def partitioned(tmp_path):
    identity = ContextVar("test_partition_identity")
    worlds, specs = {}, {}
    with ExitStack() as stack:
        for tenant in ("tenant-a", "tenant-b"):
            path = tmp_path / tenant
            path.mkdir()
            item = stack.enter_context(contextmanager(world.__wrapped__)(path))
            runtime, repo, adapter, _, state, obj, rel = item
            # Rebind the synthetic default objects for the second tenant.
            for identifier in ("asset", "order"):
                adapter.bind_object(identifier, tenant_id=tenant)
                adapter.bind_object_sources(identifier, frozenset({"synthetic-source"}))
            for identifier in ("r1", "r2"):
                rel(identifier, tenant=tenant)
                adapter.bind_relationship_sources(identifier, frozenset({"synthetic-source"}))
            access = RelationshipSourceAccess(
                actor_id="actor",
                tenant_id=tenant,
                actor_roles=frozenset({"reader"}),
                source_ids=frozenset({"synthetic-source"}),
                rights_version="v1",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            specs[tenant] = RelationshipQualificationPartition(
                CEPIOApplicationService(runtime),
                adapter,
                lambda _, grants=state["grants"]: grants,
                lambda context, access=access: access.model_copy(
                    update={"actor_id": context.actor_id}
                ),
            )
            worlds[tenant] = item
        router = RelationshipQualificationPartitions(identity.get, specs)
        yield router, identity, specs, worlds


def actor(tenant, identifier="actor"):
    return ExecutionContext(
        actor_id=identifier, tenant_id=tenant, actor_roles=frozenset({"reader"})
    )


def test_quota_exhaustion_and_actor_rotation_do_not_consume_other_tenant_budget(partitioned):
    router, identity, _, _ = partitioned
    for index in range(120):
        identity.set(actor("tenant-a", str(index)))
        assert router.read({"asset_id": "asset", "limit": 1}).links
    identity.set(actor("tenant-a", "new-actor"))
    with pytest.raises(RelationshipQualificationUnavailable):
        router.read({"asset_id": "asset"})
    identity.set(actor("tenant-b"))
    assert router.read({"asset_id": "asset"}).links
    assert len(router._boundaries) == 2


def test_foreign_mutations_do_not_invalidate_other_partition_cursor(partitioned):
    router, identity, _, worlds = partitioned
    identity.set(actor("tenant-b"))
    first = router.read({"asset_id": "asset", "limit": 1})
    worlds["tenant-a"][5]("unrelated")
    second = router.read({"asset_id": "asset", "limit": 1, "cursor": first.next_cursor})
    assert len(second.links) == 1 and second.next_cursor is None
    # Same-partition mutation still conservatively invalidates, including hidden rows.
    first = router.read({"asset_id": "asset", "limit": 1})
    worlds["tenant-b"][5]("unrelated", tenant="tenant-b")
    with pytest.raises(RelationshipQualificationUnavailable):
        router.read({"asset_id": "asset", "limit": 1, "cursor": first.next_cursor})


def test_foreign_cursor_and_payload_tenant_are_denied(partitioned):
    router, identity, _, _ = partitioned
    identity.set(actor("tenant-a"))
    first = router.read({"asset_id": "asset", "limit": 1})
    identity.set(actor("tenant-b"))
    for query in (
        {"asset_id": "asset", "limit": 1, "cursor": first.next_cursor},
        {"asset_id": "asset", "tenant_id": "tenant-a"},
    ):
        with pytest.raises(RelationshipQualificationUnavailable):
            router.read(query)
    with pytest.raises(LookupError):
        router._context.get()


def test_unknown_tenants_do_not_create_partitions_or_consume_known_quotas(partitioned):
    router, identity, _, _ = partitioned
    for index in range(150):
        identity.set(actor(f"unknown-{index}"))
        with pytest.raises(RelationshipQualificationUnavailable):
            router.read({"asset_id": "asset"})
    assert all(boundary._total == 0 for boundary in router._boundaries.values())
    identity.set(None)
    with pytest.raises(RelationshipQualificationUnavailable):
        router.read({"asset_id": "asset"})


def test_saturated_partition_does_not_block_other_tenant(partitioned):
    router, identity, _, _ = partitioned
    boundary = router._boundaries["tenant-a"]
    for _ in range(4):
        assert boundary._slots.acquire(blocking=False)
    try:
        identity.set(actor("tenant-a"))
        with pytest.raises(RelationshipQualificationUnavailable):
            router.read({"asset_id": "asset"})
        identity.set(actor("tenant-b"))
        assert router.read({"asset_id": "asset"}).links
    finally:
        for _ in range(4):
            boundary._slots.release()


def test_database_contention_is_confined_to_its_partition(partitioned):
    router, identity, _, worlds = partitioned
    entered, release = Event(), Event()

    def hold():
        with worlds["tenant-a"][1]._lock:
            entered.set()
            assert release.wait(5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(hold)
        assert entered.wait(5)
        try:
            identity.set(actor("tenant-a"))
            with pytest.raises(RelationshipQualificationUnavailable):
                router.read({"asset_id": "asset"})
            identity.set(actor("tenant-b"))
            assert router.read({"asset_id": "asset"}).links
        finally:
            release.set()
        future.result()


def test_shared_repository_rejected_before_admission(partitioned):
    _, identity, specs, _ = partitioned
    with pytest.raises(ValueError, match="separate repositories"):
        RelationshipQualificationPartitions(
            identity.get, {"tenant-a": specs["tenant-a"], "tenant-b": specs["tenant-a"]}
        )


def test_separate_connections_to_same_file_rejected(partitioned):
    _, identity, specs, worlds = partitioned
    repo = SQLiteRepository(worlds["tenant-a"][1].path)
    try:
        other = replace(specs["tenant-b"], adapter=SQLiteRelationshipPageAdapter(repo))
        with pytest.raises(ValueError, match="share a database file"):
            RelationshipQualificationPartitions(
                identity.get, {"tenant-a": specs["tenant-a"], "tenant-b": other}
            )
    finally:
        repo.close()


def test_foreign_tenant_bindings_rejected(partitioned):
    _, identity, specs, worlds = partitioned
    worlds["tenant-a"][5]("foreign", tenant="tenant-c")
    with pytest.raises(ValueError, match="foreign tenant bindings"):
        RelationshipQualificationPartitions(identity.get, specs)


@pytest.mark.parametrize("tenant", ["", " ", "x" * 513, 123])
def test_invalid_tenant_configuration_rejected(partitioned, tenant):
    _, identity, specs, _ = partitioned
    with pytest.raises(ValueError, match="tenant identifiers"):
        RelationshipQualificationPartitions(identity.get, {tenant: specs["tenant-a"]})


def test_partition_count_is_fixed_and_bounded(partitioned):
    _, identity, specs, _ = partitioned
    for config in ({}, {str(n): specs["tenant-a"] for n in range(17)}):
        with pytest.raises(ValueError, match="one to sixteen"):
            RelationshipQualificationPartitions(identity.get, config)


def test_concurrent_tenants_use_one_captured_request_local_identity(partitioned):
    from threading import Barrier

    _, identity, specs, _ = partitioned
    entered = Barrier(2)

    def resolver(original, context):
        entered.wait(timeout=5)
        return original(context)

    isolated = {
        tenant: replace(
            spec,
            source_access=lambda context, original=spec.source_access: resolver(original, context),
        )
        for tenant, spec in specs.items()
    }
    calls = ContextVar("identity_call_count", default=0)

    def capture():
        calls.set(calls.get() + 1)
        return identity.get()

    router = RelationshipQualificationPartitions(capture, isolated)

    def read(tenant):
        identity.set(actor(tenant))
        result = router.read({"asset_id": "asset", "limit": 1})
        assert calls.get() == 1
        with pytest.raises(LookupError):
            router._context.get()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(read, tenant) for tenant in specs]
        pages = [future.result() for future in futures]
    assert all(len(page.links) == 1 for page in pages)
    assert pages[0].next_cursor != pages[1].next_cursor


def test_hardlinked_database_alias_is_not_a_resource_partition(partitioned, tmp_path):
    import os

    _, identity, specs, worlds = partitioned
    alias = tmp_path / "alias.db"
    os.link(worlds["tenant-a"][1].path, alias)
    repo = SQLiteRepository(alias)
    try:
        other = replace(specs["tenant-b"], adapter=SQLiteRelationshipPageAdapter(repo))
        with pytest.raises(ValueError, match="share a database file"):
            RelationshipQualificationPartitions(
                identity.get, {"tenant-a": specs["tenant-a"], "tenant-b": other}
            )
    finally:
        repo.close()
