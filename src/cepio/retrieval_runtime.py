"""Planning, fusion, and bounded context integration for CEPIO retrieval."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Mapping

from pydantic import BaseModel, Field

from .capability_routing import CapabilityRouter
from .memory import (
    ContextAssembler,
    ContextAssemblyResult,
    ContextBudget,
    ContextCandidate,
    ContextStatus,
    MemoryRecord,
)
from .retrieval_contracts import (
    CapabilityGraphProjector,
    CapabilityRoutingResult,
    RetrievalBackend,
    RetrievalIntent,
    RetrievalMetrics,
    RetrievalPlan,
    RetrievalResult,
    RetrievalStatus,
    RetrievalStep,
    RetrievalStrategy,
    RetrievedMemory,
)

from .sovereignty import (
    IntelligenceSovereigntyContract,
    PermittedUse,
    SovereigntyDenied,
    authorize_source_use,
)


class RetrievalPlanner:
    """Build bounded backend-independent retrieval plans from a routed intent."""

    def __init__(self, graph: CapabilityGraphProjector | None = None) -> None:
        self.graph = graph

    def plan(
        self,
        intent: RetrievalIntent,
        routing: CapabilityRoutingResult,
        *,
        available_strategies: set[RetrievalStrategy],
    ) -> RetrievalPlan:
        if routing.blocked:
            return RetrievalPlan(
                routing=routing,
                max_candidates=intent.max_candidates,
                required_capability_ids=intent.required_capability_ids,
            )

        capability_ids = {item.capability_id for item in routing.routes}
        routed_capability_ids = set(capability_ids)
        if self.graph is not None and capability_ids:
            expanded = self.graph.expand(
                capability_ids,
                max_results=max(0, intent.max_capabilities - len(capability_ids)),
            )
            capability_ids.update(item.capability_id for item in expanded)

        steps: list[RetrievalStep] = []
        if RetrievalStrategy.STRUCTURED in available_strategies:
            steps.append(
                RetrievalStep(
                    id="structured",
                    strategy=RetrievalStrategy.STRUCTURED,
                    required=True,
                    tenant_id=intent.tenant_id,
                    kinds=intent.kinds,
                    tags=intent.tags,
                    capability_ids=capability_ids,
                    limit=intent.max_candidates,
                    at=intent.at,
                )
            )

        if intent.query_text:
            for strategy in (
                RetrievalStrategy.LEXICAL,
                RetrievalStrategy.VECTOR,
                RetrievalStrategy.GRAPH,
            ):
                if strategy in available_strategies:
                    steps.append(
                        RetrievalStep(
                            id=strategy.value.lower(),
                            strategy=strategy,
                            query_text=intent.query_text,
                            tenant_id=intent.tenant_id,
                            kinds=intent.kinds,
                            tags=intent.tags,
                            capability_ids=capability_ids,
                            limit=intent.max_candidates,
                            at=intent.at,
                        )
                    )

        return RetrievalPlan(
            routing=routing,
            steps=steps[: intent.max_backend_requests],
            max_candidates=intent.max_candidates,
            required_capability_ids=intent.required_capability_ids,
            expanded_capability_ids=capability_ids - routed_capability_ids,
        )


class _FusedHit(BaseModel):
    record: MemoryRecord
    rrf: float = 0.0
    strategies: set[RetrievalStrategy] = Field(default_factory=set)
    backend_ranks: dict[str, int] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class RetrievalEngine:
    """Execute a routed plan with boundary filtering and deterministic rank fusion."""

    def __init__(
        self,
        router: CapabilityRouter,
        planner: RetrievalPlanner,
        backends: list[RetrievalBackend],
        *,
        rrf_k: int = 60,
    ) -> None:
        self.router = router
        self.planner = planner
        strategies = [item.strategy for item in backends]
        if len(strategies) != len(set(strategies)):
            raise ValueError("retrieval engine requires one backend per strategy")
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        self.backends = {item.strategy: item for item in backends}
        self.rrf_k = rrf_k
        self.sovereignty_records: Mapping[str, IntelligenceSovereigntyContract] = {}
        self.require_source_tags = False

    def configure_source_rights(
        self,
        records: Mapping[str, IntelligenceSovereigntyContract],
        *,
        require_source_tags: bool = True,
    ) -> None:
        """Configure a trusted host-supplied snapshot; never use request assertions."""

        self.sovereignty_records = dict(records)
        self.require_source_tags = require_source_tags

    def retrieve(self, intent: RetrievalIntent) -> RetrievalResult:
        routing = self.router.route(intent)
        plan = self.planner.plan(
            intent,
            routing,
            available_strategies=set(self.backends),
        )
        metrics = RetrievalMetrics(route_count=len(routing.routes))
        if routing.blocked:
            missing = ", ".join(sorted(routing.unresolved_required_capabilities))
            return RetrievalResult(
                status=RetrievalStatus.BLOCKED,
                routing=routing,
                plan=plan,
                blockers=[f"required capabilities are not registered: {missing}"],
                metrics=metrics,
            )

        fused: dict[str, _FusedHit] = {}
        warnings: list[str] = []
        for step in plan.steps:
            backend = self.backends.get(step.strategy)
            if backend is None:
                if step.required:
                    return RetrievalResult(
                        status=RetrievalStatus.BLOCKED,
                        routing=routing,
                        plan=plan,
                        blockers=[f"required retrieval backend unavailable: {step.strategy.value}"],
                        metrics=metrics,
                    )
                continue

            metrics.backend_requests += 1
            try:
                hits = backend.search(step)
            except Exception as exc:
                metrics.backend_failures += 1
                if step.required:
                    return RetrievalResult(
                        status=RetrievalStatus.BLOCKED,
                        routing=routing,
                        plan=plan,
                        blockers=[f"required retrieval step {step.id} failed: {exc}"],
                        metrics=metrics,
                    )
                warnings.append(f"optional retrieval step {step.id} failed: {exc}")
                continue

            metrics.raw_hits += len(hits)
            for hit in hits:
                record = hit.record
                if not record.visible_to(intent.tenant_id) or record.expired_at(intent.at):
                    metrics.dropped_boundary_hits += 1
                    continue
                if record.sovereignty_source_id is None:
                    if self.require_source_tags:
                        metrics.dropped_boundary_hits += 1
                        continue
                else:
                    # A tagged derivative must identify all known contributing
                    # sources. Query-time is never a substitute for current rights.
                    sources = set(record.provenance.source_ids)
                    sources.add(record.sovereignty_source_id)
                    if self.require_source_tags and (
                        not record.provenance.source_ids
                        or record.sovereignty_source_id not in record.provenance.source_ids
                    ):
                        metrics.dropped_boundary_hits += 1
                        continue
                    try:
                        for source_id in sorted(sources):
                            authorize_source_use(
                                source_id,
                                records=self.sovereignty_records,
                                use=(
                                    PermittedUse.SHARED_RETRIEVAL
                                    if record.scope.value == "GLOBAL"
                                    else PermittedUse.TENANT_INFERENCE
                                ),
                                tenant_id=intent.tenant_id,
                                at=datetime.now(timezone.utc),
                            )
                    except SovereigntyDenied:
                        metrics.dropped_boundary_hits += 1
                        continue
                entry = fused.setdefault(
                    record.id,
                    _FusedHit(record=record.model_copy(deep=True)),
                )
                entry.rrf += 1.0 / (self.rrf_k + hit.rank)
                entry.strategies.add(hit.strategy)
                entry.backend_ranks[hit.strategy.value] = hit.rank
                entry.reasons.extend(hit.reasons)

        metrics.fused_hits = len(fused)
        ordered = sorted(fused.items(), key=lambda item: (-item[1].rrf, item[0]))
        best_rrf = ordered[0][1].rrf if ordered else 1.0

        candidates: list[RetrievedMemory] = []
        for _memory_id, entry in ordered[: plan.max_candidates]:
            candidates.append(
                RetrievedMemory(
                    record=entry.record,
                    score=round(entry.rrf / best_rrf, 6),
                    strategies=entry.strategies,
                    backend_ranks=entry.backend_ranks,
                    reasons=sorted(set(entry.reasons)),
                )
            )

        metrics.selected_hits = len(candidates)
        covered = (
            set().union(*(item.record.capability_ids for item in candidates))
            if candidates
            else set()
        )
        missing_required = plan.required_capability_ids - covered
        if missing_required:
            missing = ", ".join(sorted(missing_required))
            return RetrievalResult(
                status=RetrievalStatus.BLOCKED,
                routing=routing,
                plan=plan,
                candidates=[],
                blockers=[f"required capability evidence was not retrieved: {missing}"],
                warnings=warnings,
                metrics=metrics,
            )

        return RetrievalResult(
            status=RetrievalStatus.READY,
            routing=routing,
            plan=plan,
            candidates=candidates,
            warnings=warnings,
            metrics=metrics,
        )


class RetrievalContextResult(BaseModel):
    status: RetrievalStatus
    retrieval: RetrievalResult
    context: ContextAssemblyResult | None = None
    blockers: list[str] = Field(default_factory=list)


class RetrievalContextPipeline:
    """Connect retrieval output to the bounded Memory v0.1 ContextAssembler."""

    def __init__(
        self,
        engine: RetrievalEngine,
        assembler: ContextAssembler | None = None,
    ) -> None:
        self.engine = engine
        self.assembler = assembler or ContextAssembler()

    @staticmethod
    def _estimated_tokens(record: MemoryRecord) -> int:
        material = " ".join([record.summary, *sorted(record.tags), *sorted(record.capability_ids)])
        return max(1, math.ceil(len(material) / 4))

    def execute(
        self,
        intent: RetrievalIntent,
        *,
        budget: ContextBudget,
    ) -> RetrievalContextResult:
        retrieval = self.engine.retrieve(intent)
        if retrieval.status == RetrievalStatus.BLOCKED:
            return RetrievalContextResult(
                status=RetrievalStatus.BLOCKED,
                retrieval=retrieval,
                blockers=retrieval.blockers,
            )

        candidates = [
            ContextCandidate(
                record=item.record,
                estimated_tokens=self._estimated_tokens(item.record),
                relevance=item.score,
                priority=100
                if not item.record.capability_ids.isdisjoint(intent.required_capability_ids)
                else 0,
                required=not item.record.capability_ids.isdisjoint(intent.required_capability_ids),
                evidence_items=int(item.record.reference is not None),
                capability_ids=item.record.capability_ids,
            )
            for item in retrieval.candidates
        ]
        context = self.assembler.assemble(
            candidates,
            tenant_id=intent.tenant_id,
            budget=budget,
            at=intent.at,
        )
        if context.status == ContextStatus.BLOCKED:
            return RetrievalContextResult(
                status=RetrievalStatus.BLOCKED,
                retrieval=retrieval,
                context=context,
                blockers=context.blockers,
            )
        return RetrievalContextResult(
            status=RetrievalStatus.READY,
            retrieval=retrieval,
            context=context,
        )
