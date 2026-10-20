"""Typed contracts for CEPIO capability-routed retrieval."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from .memory import MemoryKind, MemoryRecord, utcnow


class RetrievalStrategy(str, Enum):
    STRUCTURED = "STRUCTURED"
    LEXICAL = "LEXICAL"
    VECTOR = "VECTOR"
    GRAPH = "GRAPH"


class RetrievalStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class RetrievalBackendError(RuntimeError):
    """Raised when a planned backend search cannot be executed."""


class CapabilityRoute(BaseModel):
    capability_id: str
    score: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class CapabilityRoutingResult(BaseModel):
    routes: list[CapabilityRoute] = Field(default_factory=list)
    unresolved_required_capabilities: set[str] = Field(default_factory=set)

    @property
    def blocked(self) -> bool:
        return bool(self.unresolved_required_capabilities)


class RetrievalIntent(BaseModel):
    query_text: str = ""
    tenant_id: str | None = None
    kinds: set[MemoryKind] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)
    capability_hints: set[str] = Field(default_factory=set)
    required_capability_ids: set[str] = Field(default_factory=set)
    max_capabilities: int = Field(default=5, ge=1, le=50)
    max_candidates: int = Field(default=50, ge=1, le=500)
    max_backend_requests: int = Field(default=4, ge=1, le=4)
    at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def require_selector(self) -> "RetrievalIntent":
        if not any(
            (
                self.query_text.strip(),
                self.kinds,
                self.tags,
                self.capability_hints,
                self.required_capability_ids,
            )
        ):
            raise ValueError("retrieval intent requires at least one selector")
        return self


class GraphExpansion(BaseModel):
    capability_id: str
    score: float = Field(ge=0.0, le=1.0)
    source_capability_ids: set[str] = Field(default_factory=set)


class CapabilityGraphProjector(Protocol):
    def expand(
        self,
        capability_ids: set[str],
        *,
        max_results: int,
    ) -> list[GraphExpansion]: ...


class RetrievalStep(BaseModel):
    id: str
    strategy: RetrievalStrategy
    required: bool = False
    query_text: str = ""
    tenant_id: str | None = None
    kinds: set[MemoryKind] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)
    capability_ids: set[str] = Field(default_factory=set)
    limit: int = Field(default=50, ge=1, le=500)
    at: datetime = Field(default_factory=utcnow)


class RetrievalPlan(BaseModel):
    routing: CapabilityRoutingResult
    steps: list[RetrievalStep] = Field(default_factory=list)
    max_candidates: int = Field(default=50, ge=1, le=500)
    required_capability_ids: set[str] = Field(default_factory=set)
    expanded_capability_ids: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def unique_steps(self) -> "RetrievalPlan":
        ids = [item.id for item in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("retrieval plan contains duplicate step IDs")
        return self


class BackendHit(BaseModel):
    record: MemoryRecord
    strategy: RetrievalStrategy
    score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    reasons: list[str] = Field(default_factory=list)


class RetrievalBackend(Protocol):
    strategy: RetrievalStrategy

    def search(self, step: RetrievalStep) -> list[BackendHit]: ...


class MemorySearchIndex(Protocol):
    def upsert(self, record: MemoryRecord) -> None: ...

    def remove(self, memory_id: str) -> bool: ...

    def search(self, step: RetrievalStep) -> list[BackendHit]: ...


class RetrievedMemory(BaseModel):
    record: MemoryRecord
    score: float = Field(ge=0.0, le=1.0)
    strategies: set[RetrievalStrategy] = Field(default_factory=set)
    backend_ranks: dict[str, int] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class RetrievalMetrics(BaseModel):
    route_count: int = 0
    backend_requests: int = 0
    backend_failures: int = 0
    raw_hits: int = 0
    fused_hits: int = 0
    selected_hits: int = 0
    dropped_boundary_hits: int = 0


class RetrievalResult(BaseModel):
    status: RetrievalStatus
    routing: CapabilityRoutingResult
    plan: RetrievalPlan
    candidates: list[RetrievedMemory] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
