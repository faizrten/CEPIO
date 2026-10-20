from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.memory import (
    ContextAssembler,
    ContextBudget,
    ContextCandidate,
    ContextStatus,
    InMemoryMemoryStore,
    MemoryAccessError,
    MemoryBoundaryError,
    MemoryKind,
    MemoryProvenance,
    MemoryQuery,
    MemoryRecord,
    MemoryReference,
    MemoryScope,
    SQLiteMemoryStore,
)

NOW = datetime(2026, 10, 20, 5, 0, tzinfo=timezone.utc)


def memory(
    memory_id: str = "m1",
    *,
    kind: str = "SEMANTIC",
    scope: str = "GLOBAL",
    tenant_id: str | None = None,
    customer_specific: bool = False,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
    capability_ids: set[str] | None = None,
    tags: set[str] | None = None,
) -> MemoryRecord:
    return MemoryRecord.model_validate(
        {
            "id": memory_id,
            "kind": kind,
            "scope": scope,
            "tenant_id": tenant_id,
            "summary": memory_id,
            "provenance": {
                "source_kind": "qualified-capability",
                "source_ids": ["source-1"],
                "derived_from": [],
                "customer_specific": customer_specific,
            },
            "reference": {
                "source_system": "Fabric",
                "resource_type": "work-order",
                "resource_id": "WO-1",
                "binding": "fabric-sql",
                "observed_at": NOW,
                "content_hash": "abc",
            },
            "created_at": created_at,
            "expires_at": expires_at,
            "capability_ids": capability_ids or set(),
            "tags": tags or set(),
        }
    )


def candidate(
    memory_id: str,
    *,
    kind: str = "SEMANTIC",
    scope: str = "GLOBAL",
    tenant_id: str | None = None,
    tokens: int = 10,
    relevance: float = 0.5,
    priority: int = 0,
    required: bool = False,
    nodes: int = 0,
    evidence: int = 0,
    capabilities: set[str] | None = None,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
) -> ContextCandidate:
    return ContextCandidate(
        record=memory(
            memory_id,
            kind=kind,
            scope=scope,
            tenant_id=tenant_id,
            capability_ids=capabilities,
            created_at=created_at,
            expires_at=expires_at,
        ),
        estimated_tokens=tokens,
        relevance=relevance,
        priority=priority,
        required=required,
        semantic_nodes=nodes,
        evidence_items=evidence,
        capability_ids=capabilities or set(),
    )


def test_memory_contract_enforces_global_and_profile_boundaries():
    with pytest.raises(ValidationError, match="global memory cannot contain"):
        memory(tenant_id="tenant-a")
    with pytest.raises(ValidationError, match="global memory cannot contain"):
        memory(customer_specific=True)
    with pytest.raises(ValidationError, match="requires tenant_id"):
        memory(scope="TENANT")
    with pytest.raises(ValidationError, match="PROFILE kind and PROFILE scope"):
        memory(kind="PROFILE", scope="TENANT", tenant_id="tenant-a")
    with pytest.raises(ValidationError, match="PROFILE kind and PROFILE scope"):
        memory(kind="SEMANTIC", scope="PROFILE", tenant_id="tenant-a")
    with pytest.raises(ValidationError, match="expires_at must be later"):
        memory(expires_at=NOW)
    profile = memory(kind="PROFILE", scope="PROFILE", tenant_id="tenant-a")
    assert profile.scope == MemoryScope.PROFILE
    assert isinstance(profile.reference, MemoryReference)
    assert profile.provenance == MemoryProvenance(
        source_kind="qualified-capability", source_ids=["source-1"]
    )


def test_memory_visibility_and_expiry_helpers():
    global_record = memory()
    tenant_record = memory("tenant", scope="TENANT", tenant_id="tenant-a")
    expiring = memory("expiring", expires_at=NOW + timedelta(hours=1))
    assert global_record.visible_to(None)
    assert global_record.visible_to("tenant-a")
    assert tenant_record.visible_to("tenant-a")
    assert not tenant_record.visible_to("tenant-b")
    assert not expiring.expired_at(NOW)
    assert expiring.expired_at(NOW + timedelta(hours=1))


def test_store_put_get_boundary_update_and_expiry():
    store = InMemoryMemoryStore()
    original = store.put(memory("global"))
    original.summary = "mutated"
    assert store.get("global").summary == "global"
    assert store.get("missing") is None

    tenant = store.put(memory("tenant", scope="TENANT", tenant_id="tenant-a"))
    assert store.get("tenant", "tenant-a") == tenant
    with pytest.raises(MemoryAccessError, match="outside"):
        store.get("tenant", "tenant-b")
    with pytest.raises(MemoryBoundaryError, match="ownership boundary"):
        store.put(memory("tenant"))

    expired = memory(
        "expired",
        created_at=NOW - timedelta(hours=2),
        expires_at=NOW - timedelta(hours=1),
    )
    store.put(expired)
    assert store.get("expired") is None


def test_store_query_filters_scope_kind_capability_tag_expiry_and_limit():
    store = InMemoryMemoryStore()
    store.put(memory("global", capability_ids={"cap-a"}, tags={"reliability"}))
    store.put(
        memory(
            "tenant-new",
            scope="TENANT",
            tenant_id="tenant-a",
            kind="EPISODIC",
            capability_ids={"cap-a"},
            tags={"reliability"},
            created_at=NOW + timedelta(minutes=1),
        )
    )
    store.put(
        memory(
            "tenant-other",
            scope="TENANT",
            tenant_id="tenant-b",
            capability_ids={"cap-a"},
            tags={"reliability"},
        )
    )
    store.put(memory("wrong-cap", capability_ids={"cap-b"}, tags={"reliability"}))
    store.put(memory("wrong-tag", capability_ids={"cap-a"}, tags={"operations"}))
    store.put(
        memory(
            "expired",
            created_at=NOW - timedelta(hours=2),
            expires_at=NOW - timedelta(hours=1),
            capability_ids={"cap-a"},
            tags={"reliability"},
        )
    )

    query = MemoryQuery(
        tenant_id="tenant-a",
        capability_ids={"cap-a"},
        tags={"reliability"},
        at=NOW,
        limit=2,
    )
    assert [item.id for item in store.query(query)] == ["tenant-new", "global"]
    no_global = query.model_copy(update={"include_global": False})
    assert [item.id for item in store.query(no_global)] == ["tenant-new"]
    episodes = query.model_copy(update={"kinds": {MemoryKind.EPISODIC}})
    assert [item.id for item in store.query(episodes)] == ["tenant-new"]


def test_sqlite_store_persists_and_preserves_memory_boundaries(tmp_path):
    path = tmp_path / "memory.db"
    first = SQLiteMemoryStore(path)
    stored = first.put(memory("tenant", scope="TENANT", tenant_id="tenant-a"))
    first.put(memory("global", capability_ids={"cap-a"}, tags={"reliability"}))
    first.close()

    second = SQLiteMemoryStore(path)
    assert second.get("tenant", "tenant-a") == stored
    assert second.get("missing") is None
    with pytest.raises(MemoryAccessError, match="outside"):
        second.get("tenant", "tenant-b")
    with pytest.raises(MemoryBoundaryError, match="ownership boundary"):
        second.put(memory("tenant"))
    assert [item.id for item in second.query(MemoryQuery(tags={"reliability"}, at=NOW))] == [
        "global"
    ]
    assert not second.forget("missing")
    with pytest.raises(MemoryAccessError, match="deletion"):
        second.forget("tenant", "tenant-b")
    assert second.forget("tenant", "tenant-a")
    assert second.get("tenant", "tenant-a") is None
    second.close()


def test_store_forget_is_owner_scoped():
    store = InMemoryMemoryStore()
    store.put(memory("global"))
    store.put(memory("tenant", scope="TENANT", tenant_id="tenant-a"))
    assert not store.forget("missing")
    with pytest.raises(MemoryAccessError, match="deletion"):
        store.forget("global", "tenant-a")
    with pytest.raises(MemoryAccessError, match="deletion"):
        store.forget("tenant", "tenant-b")
    assert store.forget("tenant", "tenant-a")
    assert store.forget("global")


def test_context_assembler_ranks_deduplicates_filters_and_tracks_usage():
    assembler = ContextAssembler()
    result = assembler.assemble(
        [
            candidate("optional", tokens=20, relevance=0.9, capabilities={"cap-b"}),
            candidate(
                "required",
                tokens=10,
                priority=1,
                required=True,
                nodes=3,
                evidence=2,
                capabilities={"cap-a"},
            ),
            candidate("optional", tokens=5, relevance=0.1),
            candidate("foreign", scope="TENANT", tenant_id="tenant-b"),
            candidate(
                "expired",
                created_at=NOW - timedelta(minutes=1),
                expires_at=NOW - timedelta(seconds=1),
            ),
        ],
        tenant_id="tenant-a",
        budget=ContextBudget(
            max_tokens=100,
            max_capabilities=3,
            max_semantic_nodes=10,
            max_evidence_items=10,
            max_episodes=2,
        ),
        at=NOW,
    )
    assert result.status == ContextStatus.READY
    assert [item.record.id for item in result.selected] == ["required", "optional"]
    assert result.dropped_ids == ["expired", "foreign", "optional"]
    assert result.usage.tokens == 30
    assert result.usage.capabilities == 2
    assert result.usage.semantic_nodes == 3
    assert result.usage.evidence_items == 2
    assert result.usage.episodes == 0
    assert not result.blockers


@pytest.mark.parametrize(
    ("budget", "candidate_kwargs", "reason"),
    [
        (ContextBudget(max_tokens=5), {"tokens": 10}, "tokens"),
        (
            ContextBudget(max_capabilities=1),
            {"capabilities": {"cap-a", "cap-b"}},
            "capabilities",
        ),
        (ContextBudget(max_semantic_nodes=1), {"nodes": 2}, "semantic_nodes"),
        (ContextBudget(max_evidence_items=1), {"evidence": 2}, "evidence_items"),
        (ContextBudget(max_episodes=0), {"kind": "EPISODIC"}, "episodes"),
    ],
)
def test_required_context_overflow_fails_closed(budget, candidate_kwargs, reason):
    required = candidate("required", required=True, **candidate_kwargs)
    result = ContextAssembler().assemble(
        [required, candidate("optional")], tenant_id=None, budget=budget, at=NOW
    )
    assert result.status == ContextStatus.BLOCKED
    assert result.selected == []
    assert result.usage.tokens == 0
    assert result.blockers == [f"required memory required exceeds {reason} budget"]
    assert result.dropped_ids == ["optional", "required"]


def test_optional_overflow_is_dropped_and_episode_usage_is_counted():
    result = ContextAssembler().assemble(
        [
            candidate("episode", kind="EPISODIC", required=True, tokens=5),
            candidate("too-big", tokens=50),
        ],
        tenant_id=None,
        budget=ContextBudget(max_tokens=10, max_episodes=1),
        at=NOW,
    )
    assert result.status == ContextStatus.READY
    assert [item.record.id for item in result.selected] == ["episode"]
    assert result.dropped_ids == ["too-big"]
    assert result.usage.episodes == 1


def test_context_size_is_bounded_when_memory_store_grows():
    store = InMemoryMemoryStore()
    store.put(memory("relevant", capability_ids={"cap-target"}, tags={"target"}))
    for index in range(500):
        store.put(memory(f"noise-{index:03d}", capability_ids={"other"}, tags={"noise"}))
    retrieved = store.query(
        MemoryQuery(capability_ids={"cap-target"}, tags={"target"}, at=NOW, limit=50)
    )
    candidates = [
        ContextCandidate(record=item, estimated_tokens=20, relevance=1.0) for item in retrieved
    ]
    result = ContextAssembler().assemble(
        candidates, tenant_id=None, budget=ContextBudget(max_tokens=100), at=NOW
    )
    assert [item.record.id for item in result.selected] == ["relevant"]
    assert result.usage.tokens == 20
