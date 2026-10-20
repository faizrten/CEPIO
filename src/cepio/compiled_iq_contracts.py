"""Typed contracts for compiled Industry IQ runtime bundles and hot-cache acceleration."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from .capability_registry import CapabilityLayer, CapabilityMaturity, EvidenceScope


class CompilationBoundaryError(ValueError):
    """Raised when compilation would cross a CEPIO knowledge boundary."""


class ActivationStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class BundleSource(str, Enum):
    CACHE = "CACHE"
    COMPILED = "COMPILED"


class CompiledEvidenceRef(BaseModel):
    """Immutable qualification evidence retained with the compiled capability."""

    model_config = ConfigDict(frozen=True)

    id: str
    domain: str
    kind: str
    artifact: str
    question_ids: tuple[str, ...] = ()
    scope: EvidenceScope


class CompiledCapabilityBundle(BaseModel):
    """Immutable, deterministic runtime projection of one governed capability."""

    model_config = ConfigDict(frozen=True)

    contract_version: str
    compiler_version: str
    source_registry_id: str
    capability_id: str
    capability_version: str
    layer: CapabilityLayer
    maturity: CapabilityMaturity
    title: str
    description: str
    semantic_terms: tuple[str, ...] = ()
    semantic_relationships: tuple[str, ...] = ()
    personas: tuple[str, ...] = ()
    competencies: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    reasoning_patterns: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    authority_requirements: tuple[str, ...] = ()
    policy_requirements: tuple[str, ...] = ()
    industry_iq_packs: tuple[str, ...] = ()
    runtime_bindings: tuple[str, ...] = ()
    uncertainty_models: tuple[str, ...] = ()
    validated_domains: tuple[str, ...] = ()
    qualification_evidence: tuple[CompiledEvidenceRef, ...] = ()
    provenance_mode: str
    provenance_source_ids: tuple[str, ...] = ()
    provenance_decision_id: str | None = None
    source_digest: str
    bundle_digest: str

    @property
    def cache_identity(self) -> str:
        return (
            f"{self.compiler_version}:{self.source_registry_id}:"
            f"{self.capability_id}:{self.capability_version}:{self.source_digest}"
        )


class RuntimeBundlePolicy(BaseModel):
    max_cache_entries: int = Field(default=256, ge=1, le=100_000)
    ttl_seconds: int = Field(default=900, ge=1, le=86_400)
    max_bundles_per_activation: int = Field(default=5, ge=1, le=50)
    cacheable_layers: set[CapabilityLayer] = Field(
        default_factory=lambda: {
            CapabilityLayer.CORE,
            CapabilityLayer.COMMON,
            CapabilityLayer.DOMAIN,
        }
    )


class CacheStats(BaseModel):
    hits: int = 0
    misses: int = 0
    writes: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0


class CompiledBundleCache(Protocol):
    def get(self, key: str) -> CompiledCapabilityBundle | None: ...

    def put(
        self,
        key: str,
        bundle: CompiledCapabilityBundle,
        *,
        ttl_seconds: int,
    ) -> None: ...

    def invalidate_capability(self, capability_id: str) -> int: ...

    def clear(self) -> int: ...

    def stats(self) -> CacheStats: ...


class ResolvedCapability(BaseModel):
    bundle: CompiledCapabilityBundle
    source: BundleSource


class ActivationMetrics(BaseModel):
    requested_bundles: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    compilations: int = 0
    rejected_profile_bundles: int = 0


class CapabilityActivation(BaseModel):
    status: ActivationStatus
    resolved: list[ResolvedCapability] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    metrics: ActivationMetrics = Field(default_factory=ActivationMetrics)

    @property
    def bundles(self) -> list[CompiledCapabilityBundle]:
        return [item.bundle for item in self.resolved]
