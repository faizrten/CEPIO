"""Compiler, cache and activation runtime for compiled Industry IQ."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Callable

from .capability_registry import (
    CapabilityLayer,
    CapabilityRecord,
    CapabilityRegistry,
    stable_hash,
)
from .compiled_iq_contracts import (
    ActivationMetrics,
    ActivationStatus,
    BundleSource,
    CacheStats,
    CapabilityActivation,
    CompilationBoundaryError,
    CompiledBundleCache,
    CompiledCapabilityBundle,
    CompiledEvidenceRef,
    ResolvedCapability,
    RuntimeBundlePolicy,
)
from .retrieval_contracts import CapabilityRoutingResult


BUNDLE_CONTRACT_VERSION = "0.1"
COMPILER_VERSION = "0.1"


def _sorted(values: set[str]) -> tuple[str, ...]:
    return tuple(sorted(values))


def canonical_capability_payload(record: CapabilityRecord) -> dict[str, object]:
    """Canonical source payload: order-insensitive fields are explicitly sorted."""

    evidence = [
        {
            "id": item.id,
            "domain": item.domain,
            "kind": item.kind,
            "artifact": item.artifact,
            "question_ids": sorted(item.question_ids),
            "scope": item.scope.value,
            "customer_specific": item.customer_specific,
        }
        for item in sorted(record.evidence, key=lambda value: value.id)
    ]
    return {
        "id": record.id,
        "version": record.version,
        "title": record.title,
        "description": record.description,
        "layer": record.layer.value,
        "maturity": record.maturity.value,
        "semantic_terms": sorted(record.semantic_terms),
        "semantic_relationships": sorted(record.semantic_relationships),
        "personas": sorted(record.personas),
        "competencies": sorted(record.competencies),
        "evidence_requirements": sorted(record.evidence_requirements),
        "reasoning_patterns": sorted(record.reasoning_patterns),
        "skills": sorted(record.skills),
        "decisions": sorted(record.decisions),
        "authority_requirements": sorted(record.authority_requirements),
        "policy_requirements": sorted(record.policy_requirements),
        "industry_iq_packs": sorted(record.industry_iq_packs),
        "runtime_bindings": sorted(record.runtime_bindings),
        "uncertainty_models": sorted(record.uncertainty_models),
        "validated_domains": sorted(record.validated_domains),
        "evidence": evidence,
        "profile_validation_count": record.profile_validation_count,
        "provenance": {
            "mode": record.provenance.mode,
            "source_ids": sorted(record.provenance.source_ids),
            "decision_id": record.provenance.decision_id,
        },
    }


def capability_source_digest(record: CapabilityRecord) -> str:
    return stable_hash(canonical_capability_payload(record))


def capability_cache_key(
    *,
    registry_id: str,
    record: CapabilityRecord,
    compiler_version: str = COMPILER_VERSION,
) -> str:
    """Scope invalidation to the capability, never to unrelated registry growth."""

    return (
        f"{compiler_version}:{registry_id}:{record.id}:{record.version}:"
        f"{capability_source_digest(record)}"
    )


class CapabilityCompiler:
    """Compile governed capability records into immutable runtime bundles."""

    def __init__(self, *, compiler_version: str = COMPILER_VERSION) -> None:
        self.compiler_version = compiler_version

    def compile(
        self,
        record: CapabilityRecord,
        *,
        registry_id: str,
        policy: RuntimeBundlePolicy,
    ) -> CompiledCapabilityBundle:
        if record.layer == CapabilityLayer.PROFILE:
            raise CompilationBoundaryError(
                "PROFILE capabilities require tenant-bound request-time composition "
                "and cannot enter the shared compiled cache"
            )
        if record.layer not in policy.cacheable_layers:
            raise CompilationBoundaryError(
                f"capability layer {record.layer.value} is not eligible for shared compilation"
            )

        source_digest = capability_source_digest(record)
        compiled_evidence: tuple[CompiledEvidenceRef, ...] = tuple(
            CompiledEvidenceRef(
                id=item.id,
                domain=item.domain,
                kind=item.kind,
                artifact=item.artifact,
                question_ids=tuple(sorted(item.question_ids)),
                scope=item.scope,
            )
            for item in sorted(record.evidence, key=lambda value: value.id)
        )
        payload: dict[str, object] = {
            "contract_version": BUNDLE_CONTRACT_VERSION,
            "compiler_version": self.compiler_version,
            "source_registry_id": registry_id,
            "capability_id": record.id,
            "capability_version": record.version,
            "layer": record.layer,
            "maturity": record.maturity,
            "title": record.title,
            "description": record.description,
            "semantic_terms": _sorted(record.semantic_terms),
            "semantic_relationships": _sorted(record.semantic_relationships),
            "personas": _sorted(record.personas),
            "competencies": _sorted(record.competencies),
            "evidence_requirements": _sorted(record.evidence_requirements),
            "reasoning_patterns": _sorted(record.reasoning_patterns),
            "skills": _sorted(record.skills),
            "decisions": _sorted(record.decisions),
            "authority_requirements": _sorted(record.authority_requirements),
            "policy_requirements": _sorted(record.policy_requirements),
            "industry_iq_packs": _sorted(record.industry_iq_packs),
            "runtime_bindings": _sorted(record.runtime_bindings),
            "uncertainty_models": _sorted(record.uncertainty_models),
            "validated_domains": _sorted(record.validated_domains),
            "qualification_evidence": compiled_evidence,
            "provenance_mode": record.provenance.mode,
            "provenance_source_ids": tuple(sorted(record.provenance.source_ids)),
            "provenance_decision_id": record.provenance.decision_id,
            "source_digest": source_digest,
        }
        digest_payload = dict(payload)
        digest_payload["qualification_evidence"] = [
            item.model_dump(mode="json") for item in compiled_evidence
        ]
        bundle_digest = stable_hash(digest_payload)
        return CompiledCapabilityBundle.model_validate({**payload, "bundle_digest": bundle_digest})


@dataclass
class _CacheEntry:
    bundle: CompiledCapabilityBundle
    expires_at: float


class InMemoryCompiledBundleCache(CompiledBundleCache):
    """Thread-safe bounded LRU/TTL reference cache; external caches stay adapters."""

    def __init__(
        self,
        *,
        max_entries: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = RLock()

    def get(self, key: str) -> CompiledCapabilityBundle | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            if entry.expires_at <= self._clock():
                del self._entries[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                return None
            self._entries.move_to_end(key)
            self._stats.hits += 1
            return entry.bundle

    def put(
        self,
        key: str,
        bundle: CompiledCapabilityBundle,
        *,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")
        with self._lock:
            self._entries.pop(key, None)
            while len(self._entries) >= self.max_entries:
                self._entries.popitem(last=False)
                self._stats.evictions += 1
            self._entries[key] = _CacheEntry(
                bundle=bundle,
                expires_at=self._clock() + ttl_seconds,
            )
            self._stats.writes += 1

    def invalidate_capability(self, capability_id: str) -> int:
        with self._lock:
            keys = [
                key
                for key, entry in self._entries.items()
                if entry.bundle.capability_id == capability_id
            ]
            for key in keys:
                del self._entries[key]
            self._stats.invalidations += len(keys)
            return len(keys)

    def clear(self) -> int:
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._stats.invalidations += count
            return count

    def stats(self) -> CacheStats:
        with self._lock:
            return self._stats.model_copy(deep=True)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class CompiledCapabilityResolver:
    """Activate routed capabilities using deterministic compile-on-miss semantics."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        cache: CompiledBundleCache,
        policy: RuntimeBundlePolicy | None = None,
        compiler: CapabilityCompiler | None = None,
    ) -> None:
        self.registry = registry
        self.cache = cache
        self.policy = policy or RuntimeBundlePolicy()
        self.compiler = compiler or CapabilityCompiler()
        self._records = {item.id: item for item in registry.capabilities}

    def _resolve(self, record: CapabilityRecord) -> ResolvedCapability:
        key = capability_cache_key(
            registry_id=self.registry.id,
            record=record,
            compiler_version=self.compiler.compiler_version,
        )
        expected_digest = capability_source_digest(record)
        cached = self.cache.get(key)
        if (
            cached is not None
            and cached.source_digest == expected_digest
            and cached.capability_id == record.id
            and cached.capability_version == record.version
        ):
            return ResolvedCapability(bundle=cached, source=BundleSource.CACHE)

        bundle = self.compiler.compile(
            record,
            registry_id=self.registry.id,
            policy=self.policy,
        )
        self.cache.put(key, bundle, ttl_seconds=self.policy.ttl_seconds)
        return ResolvedCapability(bundle=bundle, source=BundleSource.COMPILED)

    def activate(self, capability_ids: list[str]) -> CapabilityActivation:
        unique_ids = list(dict.fromkeys(capability_ids))
        metrics = ActivationMetrics(requested_bundles=len(unique_ids))
        if len(unique_ids) > self.policy.max_bundles_per_activation:
            return CapabilityActivation(
                status=ActivationStatus.BLOCKED,
                blockers=[
                    "requested capability bundles exceed max_bundles_per_activation "
                    f"({len(unique_ids)} > {self.policy.max_bundles_per_activation})"
                ],
                metrics=metrics,
            )

        resolved: list[ResolvedCapability] = []
        blockers: list[str] = []
        for capability_id in unique_ids:
            record = self._records.get(capability_id)
            if record is None:
                blockers.append(f"capability not found: {capability_id}")
                continue
            try:
                item = self._resolve(record)
            except CompilationBoundaryError as exc:
                if record.layer == CapabilityLayer.PROFILE:
                    metrics.rejected_profile_bundles += 1
                blockers.append(str(exc))
                continue
            if item.source == BundleSource.CACHE:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1
                metrics.compilations += 1
            resolved.append(item)

        if blockers:
            return CapabilityActivation(
                status=ActivationStatus.BLOCKED,
                blockers=blockers,
                metrics=metrics,
            )
        return CapabilityActivation(
            status=ActivationStatus.READY,
            resolved=resolved,
            metrics=metrics,
        )

    def activate_routes(self, routing: CapabilityRoutingResult) -> CapabilityActivation:
        if routing.blocked:
            return CapabilityActivation(
                status=ActivationStatus.BLOCKED,
                blockers=[
                    "required capabilities unresolved: "
                    + ", ".join(sorted(routing.unresolved_required_capabilities))
                ],
                metrics=ActivationMetrics(requested_bundles=len(routing.routes)),
            )
        return self.activate([item.capability_id for item in routing.routes])

    def invalidate(self, capability_id: str) -> int:
        return self.cache.invalidate_capability(capability_id)
