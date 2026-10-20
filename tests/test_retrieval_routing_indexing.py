from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.capability_registry import CapabilityRecord, CapabilityRegistry
from cepio.memory import (
    MemoryKind,
    MemoryProvenance,
    MemoryRecord,
    MemoryScope,
)
from cepio.retrieval import (
    CapabilityRouter,
    CapabilityRoutingResult,
    InMemoryLexicalIndex,
    RegistryCapabilityGraph,
    RetrievalIntent,
    RetrievalPlan,
    RetrievalPlanner,
    RetrievalStep,
    RetrievalStrategy,
    StructuredMemoryBackend,
)

NOW = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)
TARGET = "industrial.reliability.condition-work-context"


def capability(capability_id: str, title: str, terms: set[str], evidence: set[str]):
    return CapabilityRecord(
        id=capability_id,
        version="0.1.0",
        title=title,
        description=f"{title} industrial capability",
        layer="COMMON",
        maturity="QUALIFIED",
        semantic_terms=terms,
        evidence_requirements=evidence,
        reasoning_patterns={f"{capability_id}-reasoning"},
        provenance={"mode": "synthetic-test", "source_ids": ["test-suite"]},
    )


def registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        id="test-capability-registry",
        version="0.1",
        capabilities=[
            capability(
                TARGET,
                "Condition-to-work reliability context",
                {
                    "https://cepio.org/ontology/reliability#ConditionSignal",
                    "https://cepio.org/ontology/industrial#Equipment",
                    "https://cepio.org/ontology/industrial#WorkOrder",
                },
                {"condition evidence", "work context"},
            ),
            capability(
                "industrial.reliability.failure-risk",
                "Failure risk assessment",
                {
                    "https://cepio.org/ontology/reliability#ConditionSignal",
                    "https://cepio.org/ontology/reliability#FailureEvent",
                },
                {"condition evidence", "failure context"},
            ),
            capability(
                "industrial.finance.margin",
                "Margin performance",
                {"https://cepio.org/ontology/finance#Margin"},
                {"financial evidence"},
            ),
        ],
    )


def memory(
    memory_id: str,
    summary: str,
    *,
    capabilities: set[str] | None = None,
    tags: set[str] | None = None,
    scope: MemoryScope = MemoryScope.GLOBAL,
    tenant_id: str | None = None,
    kind: MemoryKind = MemoryKind.SEMANTIC,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        kind=kind,
        scope=scope,
        tenant_id=tenant_id,
        summary=summary,
        provenance=MemoryProvenance(source_kind="synthetic-test"),
        created_at=created_at,
        expires_at=expires_at,
        capability_ids=capabilities or set(),
        tags=tags or set(),
    )


class Store:
    def __init__(self, records):
        self.records = list(records)

    def query(self, query):
        result = []
        for record in self.records:
            if record.expired_at(query.at):
                continue
            if record.scope != MemoryScope.GLOBAL and record.tenant_id != query.tenant_id:
                continue
            if query.kinds and record.kind not in query.kinds:
                continue
            if query.capability_ids and record.capability_ids.isdisjoint(query.capability_ids):
                continue
            if query.tags and record.tags.isdisjoint(query.tags):
                continue
            result.append(record)
        return result[: query.limit]


def test_router_matches_semantics_and_explicit_hints():
    routed = CapabilityRouter(registry()).route(
        RetrievalIntent(
            query_text="condition signal work order",
            capability_hints={"industrial.finance.margin"},
            max_capabilities=3,
            at=NOW,
        )
    )
    assert routed.routes[0].capability_id == "industrial.finance.margin"
    assert TARGET in {item.capability_id for item in routed.routes}
    assert any("matched:" in reason for item in routed.routes for reason in item.reasons)


def test_router_required_and_missing_capabilities_fail_closed():
    router = CapabilityRouter(registry())
    routed = router.route(RetrievalIntent(required_capability_ids={TARGET}, at=NOW))
    assert not routed.blocked
    assert routed.routes[0].score == 1.0
    assert routed.routes[0].reasons == ["required capability"]

    missing = router.route(RetrievalIntent(required_capability_ids={"missing.capability"}, at=NOW))
    assert missing.blocked
    assert missing.unresolved_required_capabilities == {"missing.capability"}


def test_registry_graph_expands_only_related_capabilities():
    graph = RegistryCapabilityGraph(registry())
    expanded = graph.expand({TARGET}, max_results=5)
    assert [item.capability_id for item in expanded] == ["industrial.reliability.failure-risk"]
    assert expanded[0].source_capability_ids == {TARGET}
    assert graph.expand({"unknown"}, max_results=5) == []


def test_planner_uses_available_strategies_graph_and_budgets():
    reg = registry()
    intent = RetrievalIntent(
        query_text="work order",
        max_capabilities=3,
        max_candidates=12,
        at=NOW,
    )
    routing = CapabilityRouter(reg).route(intent)
    plan = RetrievalPlanner(RegistryCapabilityGraph(reg)).plan(
        intent,
        routing,
        available_strategies=set(RetrievalStrategy),
    )
    assert [step.strategy for step in plan.steps] == list(RetrievalStrategy)
    assert plan.steps[0].required
    assert plan.steps[0].limit == 12
    assert "industrial.reliability.failure-risk" in plan.expanded_capability_ids

    blocked = RetrievalPlanner().plan(
        RetrievalIntent(kinds={MemoryKind.SEMANTIC}, at=NOW),
        CapabilityRoutingResult(unresolved_required_capabilities={"x"}),
        available_strategies={RetrievalStrategy.STRUCTURED},
    )
    assert blocked.steps == []


def test_intent_requires_selector_and_backend_fanout_is_bounded():
    with pytest.raises(ValidationError, match="at least one selector"):
        RetrievalIntent(at=NOW)

    reg = registry()
    intent = RetrievalIntent(
        query_text="condition work",
        capability_hints={TARGET},
        max_backend_requests=2,
        at=NOW,
    )
    plan = RetrievalPlanner().plan(
        intent,
        CapabilityRouter(reg).route(intent),
        available_strategies=set(RetrievalStrategy),
    )
    assert [item.strategy for item in plan.steps] == [
        RetrievalStrategy.STRUCTURED,
        RetrievalStrategy.LEXICAL,
    ]


def test_retrieval_plan_rejects_duplicate_step_ids():
    with pytest.raises(ValidationError, match="duplicate step"):
        RetrievalPlan(
            routing=CapabilityRoutingResult(),
            steps=[
                RetrievalStep(id="same", strategy=RetrievalStrategy.LEXICAL),
                RetrievalStep(id="same", strategy=RetrievalStrategy.VECTOR),
            ],
        )


def test_structured_backend_uses_memory_filters():
    backend = StructuredMemoryBackend(
        Store(
            [
                memory("g", "global", capabilities={TARGET}, tags={"reliability"}),
                memory(
                    "tenant",
                    "tenant",
                    capabilities={TARGET},
                    tags={"reliability"},
                    scope=MemoryScope.TENANT,
                    tenant_id="a",
                ),
                memory(
                    "foreign",
                    "foreign",
                    capabilities={TARGET},
                    tags={"reliability"},
                    scope=MemoryScope.TENANT,
                    tenant_id="b",
                ),
            ]
        )
    )
    hits = backend.search(
        RetrievalStep(
            id="structured",
            strategy=RetrievalStrategy.STRUCTURED,
            tenant_id="a",
            capability_ids={TARGET},
            tags={"reliability"},
            at=NOW,
        )
    )
    assert [item.record.id for item in hits] == ["g", "tenant"]
    assert [item.rank for item in hits] == [1, 2]


def test_lexical_index_lifecycle_scoring_and_filters():
    index = InMemoryLexicalIndex()
    index.upsert(memory("g", "pump vibration alarm", capabilities={TARGET}))
    index.upsert(
        memory(
            "tenant",
            "pump vibration work order",
            capabilities={TARGET},
            tags={"reliability"},
            scope=MemoryScope.TENANT,
            tenant_id="a",
            kind=MemoryKind.EPISODIC,
        )
    )
    index.upsert(
        memory(
            "foreign",
            "pump vibration",
            capabilities={TARGET},
            scope=MemoryScope.TENANT,
            tenant_id="b",
        )
    )
    index.upsert(
        memory(
            "expired",
            "pump vibration",
            capabilities={TARGET},
            created_at=NOW - timedelta(seconds=2),
            expires_at=NOW - timedelta(seconds=1),
        )
    )
    assert len(index) == 4

    step = RetrievalStep(
        id="lexical",
        strategy=RetrievalStrategy.LEXICAL,
        query_text="pump vibration work",
        tenant_id="a",
        capability_ids={TARGET},
        at=NOW,
    )
    hits = index.search(step)
    assert [item.record.id for item in hits] == ["tenant", "g"]
    assert hits[0].score > hits[1].score
    assert [
        item.record.id
        for item in index.search(step.model_copy(update={"kinds": {MemoryKind.EPISODIC}}))
    ] == ["tenant"]
    assert [
        item.record.id for item in index.search(step.model_copy(update={"tags": {"reliability"}}))
    ] == ["tenant"]
    assert index.search(step.model_copy(update={"capability_ids": {"other"}})) == []
    assert index.search(step.model_copy(update={"query_text": ""})) == []

    index.upsert(memory("g", "compressor temperature", capabilities={TARGET}))
    assert [item.record.id for item in index.search(step)] == ["tenant"]
    assert not index.remove("missing")
    assert index.remove("g")
    assert len(index) == 3
