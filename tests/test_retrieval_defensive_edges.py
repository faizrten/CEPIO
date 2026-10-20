from datetime import datetime, timezone

from cepio.capability_registry import CapabilityRegistry
from cepio.memory import MemoryKind, MemoryProvenance, MemoryRecord, MemoryScope
from cepio.retrieval import (
    CapabilityRouter,
    InMemoryLexicalIndex,
    RetrievalEngine,
    RetrievalIntent,
    RetrievalPlan,
    RetrievalStatus,
    RetrievalStep,
    RetrievalStrategy,
)

NOW = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)


def memory(memory_id: str, summary: str) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        kind=MemoryKind.SEMANTIC,
        scope=MemoryScope.GLOBAL,
        summary=summary,
        provenance=MemoryProvenance(source_kind="synthetic-defensive-test"),
        created_at=NOW,
    )


def empty_registry() -> CapabilityRegistry:
    return CapabilityRegistry(id="empty-test-registry", version="0.1", capabilities=[])


class OptionalMissingPlanner:
    def plan(self, intent, routing, *, available_strategies):
        return RetrievalPlan(
            routing=routing,
            steps=[
                RetrievalStep(
                    id="optional-vector",
                    strategy=RetrievalStrategy.VECTOR,
                    required=False,
                    query_text="condition",
                    at=intent.at,
                )
            ],
            max_candidates=intent.max_candidates,
        )


def test_index_remove_tolerates_missing_posting_bucket():
    index = InMemoryLexicalIndex()
    index.upsert(memory("m1", "pump vibration"))
    del index._postings["pump"]

    assert index.remove("m1")
    assert len(index) == 0


def test_index_search_ignores_stale_posting_without_matching_document_term():
    index = InMemoryLexicalIndex()
    index.upsert(memory("m1", "pump vibration"))
    index._postings["stale"].add("m1")

    hits = index.search(
        RetrievalStep(
            id="lexical",
            strategy=RetrievalStrategy.LEXICAL,
            query_text="stale",
            at=NOW,
        )
    )
    assert hits == []


def test_optional_unavailable_backend_is_skipped_without_blocking():
    engine = RetrievalEngine(
        CapabilityRouter(empty_registry()),
        OptionalMissingPlanner(),
        [],
    )
    result = engine.retrieve(RetrievalIntent(kinds={MemoryKind.SEMANTIC}, at=NOW))

    assert result.status == RetrievalStatus.READY
    assert result.candidates == []
    assert result.metrics.backend_requests == 0
