from datetime import datetime, timedelta, timezone

import pytest

from cepio.capability_registry import CapabilityRecord, CapabilityRegistry
from cepio.memory import (
    ContextBudget,
    MemoryKind,
    MemoryProvenance,
    MemoryRecord,
    MemoryReference,
    MemoryScope,
)
from cepio.retrieval import (
    BackendHit,
    CapabilityRouter,
    InMemoryLexicalIndex,
    LexicalIndexBackend,
    RetrievalBackendError,
    RetrievalContextPipeline,
    RetrievalEngine,
    RetrievalIntent,
    RetrievalPlan,
    RetrievalPlanner,
    RetrievalStatus,
    RetrievalStep,
    RetrievalStrategy,
    StructuredMemoryBackend,
)

NOW = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)
TARGET = "industrial.reliability.condition-work-context"


def registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        id="test-capability-registry",
        version="0.1",
        capabilities=[
            CapabilityRecord(
                id=TARGET,
                version="0.1.0",
                title="Condition-to-work reliability context",
                description="Resolve condition evidence into work context",
                layer="COMMON",
                maturity="QUALIFIED",
                semantic_terms={"ConditionSignal", "Equipment", "WorkOrder"},
                evidence_requirements={"condition evidence", "work context"},
                provenance={"mode": "synthetic-test", "source_ids": ["test-suite"]},
            )
        ],
    )


def memory(
    memory_id: str,
    summary: str,
    *,
    capabilities: set[str] | None = None,
    scope: MemoryScope = MemoryScope.GLOBAL,
    tenant_id: str | None = None,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
    reference: bool = False,
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        kind=MemoryKind.SEMANTIC,
        scope=scope,
        tenant_id=tenant_id,
        summary=summary,
        provenance=MemoryProvenance(source_kind="synthetic-test"),
        created_at=created_at,
        expires_at=expires_at,
        capability_ids=capabilities or set(),
        reference=MemoryReference(
            source_system="Fabric",
            resource_type="work-order",
            resource_id="WO-1",
        )
        if reference
        else None,
    )


class StaticBackend:
    def __init__(self, strategy, hits=None, error=None):
        self.strategy = strategy
        self.hits = hits or []
        self.error = error

    def search(self, step):
        if self.error:
            raise self.error
        return self.hits


class FixedPlanner:
    def __init__(self, steps):
        self.steps = steps

    def plan(self, intent, routing, *, available_strategies):
        return RetrievalPlan(
            routing=routing,
            steps=self.steps,
            max_candidates=intent.max_candidates,
            required_capability_ids=intent.required_capability_ids,
        )


class EmptyStore:
    def query(self, query):
        return []


def hit(record, strategy, rank):
    return BackendHit(record=record, strategy=strategy, score=1, rank=rank)


def test_engine_rejects_duplicate_backends_and_invalid_rrf():
    backend = StaticBackend(RetrievalStrategy.STRUCTURED)
    with pytest.raises(ValueError, match="one backend per strategy"):
        RetrievalEngine(CapabilityRouter(registry()), RetrievalPlanner(), [backend, backend])
    with pytest.raises(ValueError, match="rrf_k must be positive"):
        RetrievalEngine(CapabilityRouter(registry()), RetrievalPlanner(), [backend], rrf_k=0)


def test_hybrid_engine_fuses_deduplicates_and_caps_candidates():
    a = memory("a", "condition work", capabilities={TARGET})
    b = memory("b", "condition work", capabilities={TARGET})
    structured = StaticBackend(
        RetrievalStrategy.STRUCTURED,
        [
            hit(a, RetrievalStrategy.STRUCTURED, 1),
            hit(b, RetrievalStrategy.STRUCTURED, 2),
        ],
    )
    lexical = StaticBackend(
        RetrievalStrategy.LEXICAL,
        [
            BackendHit(
                record=b,
                strategy=RetrievalStrategy.LEXICAL,
                score=0.9,
                rank=1,
                reasons=["lexical"],
            )
        ],
    )
    result = RetrievalEngine(
        CapabilityRouter(registry()), RetrievalPlanner(), [structured, lexical]
    ).retrieve(
        RetrievalIntent(
            query_text="condition work",
            capability_hints={TARGET},
            max_candidates=1,
            at=NOW,
        )
    )
    assert result.status == RetrievalStatus.READY
    assert [item.record.id for item in result.candidates] == ["b"]
    assert result.candidates[0].strategies == {
        RetrievalStrategy.STRUCTURED,
        RetrievalStrategy.LEXICAL,
    }
    assert result.candidates[0].score == 1.0
    assert result.metrics.raw_hits == 3
    assert result.metrics.fused_hits == 2
    assert result.metrics.selected_hits == 1


def test_optional_backend_failure_degrades_and_required_failure_blocks():
    record = memory("a", "condition work", capabilities={TARGET})
    good = StaticBackend(
        RetrievalStrategy.STRUCTURED,
        [hit(record, RetrievalStrategy.STRUCTURED, 1)],
    )
    optional = StaticBackend(
        RetrievalStrategy.LEXICAL,
        error=RetrievalBackendError("search unavailable"),
    )
    result = RetrievalEngine(
        CapabilityRouter(registry()), RetrievalPlanner(), [good, optional]
    ).retrieve(RetrievalIntent(query_text="condition work", capability_hints={TARGET}, at=NOW))
    assert result.status == RetrievalStatus.READY
    assert result.metrics.backend_failures == 1
    assert result.warnings == ["optional retrieval step lexical failed: search unavailable"]

    required = StaticBackend(
        RetrievalStrategy.STRUCTURED,
        error=RetrievalBackendError("store unavailable"),
    )
    blocked = RetrievalEngine(
        CapabilityRouter(registry()), RetrievalPlanner(), [required]
    ).retrieve(RetrievalIntent(capability_hints={TARGET}, at=NOW))
    assert blocked.status == RetrievalStatus.BLOCKED
    assert blocked.blockers == ["required retrieval step structured failed: store unavailable"]


def test_required_backend_unavailable_is_fail_closed():
    engine = RetrievalEngine(
        CapabilityRouter(registry()),
        FixedPlanner(
            [
                RetrievalStep(
                    id="must-run",
                    strategy=RetrievalStrategy.VECTOR,
                    required=True,
                    at=NOW,
                )
            ]
        ),
        [],
    )
    result = engine.retrieve(RetrievalIntent(kinds={MemoryKind.SEMANTIC}, at=NOW))
    assert result.status == RetrievalStatus.BLOCKED
    assert result.blockers == ["required retrieval backend unavailable: VECTOR"]


def test_engine_defensively_drops_foreign_and_expired_hits():
    foreign = memory(
        "foreign",
        "leak",
        scope=MemoryScope.TENANT,
        tenant_id="b",
    )
    expired = memory(
        "expired",
        "old",
        created_at=NOW - timedelta(seconds=2),
        expires_at=NOW - timedelta(seconds=1),
    )
    backend = StaticBackend(
        RetrievalStrategy.STRUCTURED,
        [
            hit(foreign, RetrievalStrategy.STRUCTURED, 1),
            hit(expired, RetrievalStrategy.STRUCTURED, 2),
        ],
    )
    result = RetrievalEngine(CapabilityRouter(registry()), RetrievalPlanner(), [backend]).retrieve(
        RetrievalIntent(tenant_id="a", kinds={MemoryKind.SEMANTIC}, at=NOW)
    )
    assert result.status == RetrievalStatus.READY
    assert result.candidates == []
    assert result.metrics.dropped_boundary_hits == 2


def test_required_capability_must_have_retrieved_evidence():
    backend = StaticBackend(
        RetrievalStrategy.STRUCTURED,
        [
            hit(
                memory("other", "unrelated", capabilities={"other"}),
                RetrievalStrategy.STRUCTURED,
                1,
            )
        ],
    )
    result = RetrievalEngine(CapabilityRouter(registry()), RetrievalPlanner(), [backend]).retrieve(
        RetrievalIntent(required_capability_ids={TARGET}, at=NOW)
    )
    assert result.status == RetrievalStatus.BLOCKED
    assert result.candidates == []
    assert result.blockers == [f"required capability evidence was not retrieved: {TARGET}"]


def test_pipeline_connects_retrieval_to_bounded_context():
    record = memory(
        "evidence",
        "critical condition evidence for work readiness",
        capabilities={TARGET},
        reference=True,
    )
    backend = StaticBackend(
        RetrievalStrategy.STRUCTURED,
        [hit(record, RetrievalStrategy.STRUCTURED, 1)],
    )
    pipeline = RetrievalContextPipeline(
        RetrievalEngine(CapabilityRouter(registry()), RetrievalPlanner(), [backend])
    )
    intent = RetrievalIntent(required_capability_ids={TARGET}, at=NOW)

    ready = pipeline.execute(intent, budget=ContextBudget(max_tokens=100))
    assert ready.status == RetrievalStatus.READY
    assert ready.context is not None
    assert [item.record.id for item in ready.context.selected] == ["evidence"]
    assert ready.context.usage.evidence_items == 1

    blocked = pipeline.execute(intent, budget=ContextBudget(max_tokens=1))
    assert blocked.status == RetrievalStatus.BLOCKED
    assert blocked.context is not None
    assert "tokens budget" in blocked.blockers[0]


def test_pipeline_propagates_retrieval_blockers():
    pipeline = RetrievalContextPipeline(
        RetrievalEngine(
            CapabilityRouter(registry()),
            RetrievalPlanner(),
            [StaticBackend(RetrievalStrategy.STRUCTURED)],
        )
    )
    result = pipeline.execute(
        RetrievalIntent(required_capability_ids={"missing"}, at=NOW),
        budget=ContextBudget(),
    )
    assert result.status == RetrievalStatus.BLOCKED
    assert result.context is None
    assert "not registered" in result.blockers[0]


def test_vector_adapter_plugs_in_without_engine_changes():
    record = memory("vector", "condition work", capabilities={TARGET})
    vector = StaticBackend(
        RetrievalStrategy.VECTOR,
        [hit(record, RetrievalStrategy.VECTOR, 1)],
    )
    structured = StaticBackend(RetrievalStrategy.STRUCTURED, [])
    result = RetrievalEngine(
        CapabilityRouter(registry()), RetrievalPlanner(), [structured, vector]
    ).retrieve(
        RetrievalIntent(
            query_text="condition work",
            capability_hints={TARGET},
            at=NOW,
        )
    )
    assert result.status == RetrievalStatus.READY
    assert result.candidates[0].record.id == "vector"
    assert result.candidates[0].strategies == {RetrievalStrategy.VECTOR}


def test_lexical_candidate_set_stays_bounded_as_index_grows():
    index = InMemoryLexicalIndex()
    index.upsert(memory("target", "pump vibration work order", capabilities={TARGET}))
    for number in range(1000):
        index.upsert(memory(f"noise-{number:04d}", "finance margin unrelated"))

    result = RetrievalEngine(
        CapabilityRouter(registry()),
        RetrievalPlanner(),
        [StructuredMemoryBackend(EmptyStore()), LexicalIndexBackend(index)],
    ).retrieve(
        RetrievalIntent(
            query_text="pump vibration",
            capability_hints={TARGET},
            max_candidates=5,
            at=NOW,
        )
    )
    assert [item.record.id for item in result.candidates] == ["target"]
    assert result.metrics.raw_hits == 1
    assert result.metrics.selected_hits == 1
