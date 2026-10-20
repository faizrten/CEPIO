"""Public facade for CEPIO Retrieval & Indexing v0.1."""

from .capability_routing import CapabilityRouter, RegistryCapabilityGraph
from .retrieval_contracts import (
    BackendHit,
    CapabilityGraphProjector,
    CapabilityRoute,
    CapabilityRoutingResult,
    GraphExpansion,
    MemorySearchIndex,
    RetrievedMemory,
    RetrievalBackend,
    RetrievalBackendError,
    RetrievalIntent,
    RetrievalMetrics,
    RetrievalPlan,
    RetrievalResult,
    RetrievalStatus,
    RetrievalStep,
    RetrievalStrategy,
)
from .retrieval_index import (
    InMemoryLexicalIndex,
    LexicalIndexBackend,
    LexicalIndexDocument,
    StructuredMemoryBackend,
)
from .retrieval_runtime import (
    RetrievalContextPipeline,
    RetrievalContextResult,
    RetrievalEngine,
    RetrievalPlanner,
)

__all__ = [
    "BackendHit",
    "CapabilityGraphProjector",
    "CapabilityRoute",
    "CapabilityRouter",
    "CapabilityRoutingResult",
    "GraphExpansion",
    "InMemoryLexicalIndex",
    "LexicalIndexBackend",
    "LexicalIndexDocument",
    "MemorySearchIndex",
    "RegistryCapabilityGraph",
    "RetrievedMemory",
    "RetrievalBackend",
    "RetrievalBackendError",
    "RetrievalContextPipeline",
    "RetrievalContextResult",
    "RetrievalEngine",
    "RetrievalIntent",
    "RetrievalMetrics",
    "RetrievalPlan",
    "RetrievalPlanner",
    "RetrievalResult",
    "RetrievalStatus",
    "RetrievalStep",
    "RetrievalStrategy",
    "StructuredMemoryBackend",
]
