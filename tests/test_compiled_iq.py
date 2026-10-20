from __future__ import annotations

import pytest
from pydantic import ValidationError

from cepio.capability_registry import (
    CapabilityEvidenceRef,
    CapabilityLayer,
    CapabilityMaturity,
    CapabilityProvenance,
    CapabilityRecord,
    CapabilityRegistry,
    EvidenceScope,
)
from cepio.compiled_iq import (
    ActivationStatus,
    BundleSource,
    CapabilityCompiler,
    CompilationBoundaryError,
    CompiledCapabilityResolver,
    InMemoryCompiledBundleCache,
    RuntimeBundlePolicy,
    canonical_capability_payload,
    capability_cache_key,
    capability_source_digest,
)
from cepio.retrieval_contracts import CapabilityRoute, CapabilityRoutingResult


def capability(
    capability_id: str = "industrial.reliability.condition-work-context",
    *,
    layer: CapabilityLayer = CapabilityLayer.COMMON,
    title: str = "Condition to work context",
    version: str = "1.0",
) -> CapabilityRecord:
    return CapabilityRecord(
        id=capability_id,
        version=version,
        title=title,
        description="Relate asset condition to governed work decisions.",
        layer=layer,
        maturity=CapabilityMaturity.QUALIFIED,
        semantic_terms={"WorkOrder", "ConditionAssessment"},
        semantic_relationships={"ConditionAssessment->WorkOrder"},
        personas={"reliability-engineer"},
        competencies={"assess-condition", "prioritize-work"},
        evidence_requirements={"condition-evidence", "work-history"},
        reasoning_patterns={"condition-to-consequence"},
        skills={"skill.condition-review"},
        decisions={"decision.maintenance-priority"},
        authority_requirements={"maintenance-approval"},
        policy_requirements={"policy.operating-risk"},
        industry_iq_packs={"pack.reliability"},
        runtime_bindings={"binding.historian", "binding.cmms"},
        uncertainty_models={"uncertainty.failure-risk"},
        validated_domains={"drilling-contractor", "refinery-process-manufacturing"},
        evidence=[
            CapabilityEvidenceRef(
                id="evidence-2",
                domain="refinery-process-manufacturing",
                kind="semantic-eval",
                artifact="evals/refinery/result.json",
                question_ids={"Q2", "Q1"},
                scope=EvidenceScope.COMMON,
            ),
            CapabilityEvidenceRef(
                id="evidence-1",
                domain="drilling-contractor",
                kind="semantic-eval",
                artifact="evals/drilling/result.json",
                question_ids={"Q3"},
                scope=EvidenceScope.COMMON,
            ),
        ],
        provenance=CapabilityProvenance(
            mode="promotion",
            source_ids=["refinery", "drilling"],
            decision_id="decision-1",
        ),
    )


def registry(*records: CapabilityRecord, version: str = "1") -> CapabilityRegistry:
    return CapabilityRegistry(id="cepio-capabilities", version=version, capabilities=list(records))


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


def test_compiler_is_deterministic_and_canonical() -> None:
    record = capability()
    compiler = CapabilityCompiler()
    policy = RuntimeBundlePolicy()
    first = compiler.compile(record, registry_id="cepio-capabilities", policy=policy)

    reordered = record.model_copy(
        update={
            "semantic_terms": set(reversed(sorted(record.semantic_terms))),
            "evidence": list(reversed(record.evidence)),
            "provenance": record.provenance.model_copy(
                update={"source_ids": list(reversed(record.provenance.source_ids))}
            ),
        }
    )
    second = compiler.compile(reordered, registry_id="cepio-capabilities", policy=policy)

    assert first.bundle_digest == second.bundle_digest
    assert first.source_digest == second.source_digest
    assert first.semantic_terms == tuple(sorted(record.semantic_terms))
    assert [item.id for item in first.qualification_evidence] == ["evidence-1", "evidence-2"]
    assert first.provenance_source_ids == ("drilling", "refinery")
    assert canonical_capability_payload(record)["semantic_terms"] == sorted(record.semantic_terms)


def test_bundle_is_immutable_and_cache_identity_matches_key() -> None:
    record = capability()
    bundle = CapabilityCompiler().compile(
        record,
        registry_id="cepio-capabilities",
        policy=RuntimeBundlePolicy(),
    )
    assert bundle.cache_identity == capability_cache_key(
        registry_id="cepio-capabilities",
        record=record,
    )
    with pytest.raises(ValidationError):
        bundle.title = "mutated"  # type: ignore[misc]


def test_profile_compilation_is_hard_blocked_even_if_policy_requests_it() -> None:
    record = capability(layer=CapabilityLayer.PROFILE)
    policy = RuntimeBundlePolicy(
        cacheable_layers={
            CapabilityLayer.CORE,
            CapabilityLayer.COMMON,
            CapabilityLayer.DOMAIN,
            CapabilityLayer.PROFILE,
        }
    )
    with pytest.raises(CompilationBoundaryError, match="tenant-bound"):
        CapabilityCompiler().compile(record, registry_id="cepio-capabilities", policy=policy)


def test_non_cacheable_layer_is_blocked_by_policy() -> None:
    record = capability(layer=CapabilityLayer.DOMAIN)
    policy = RuntimeBundlePolicy(cacheable_layers={CapabilityLayer.CORE, CapabilityLayer.COMMON})
    with pytest.raises(CompilationBoundaryError, match="not eligible"):
        CapabilityCompiler().compile(record, registry_id="cepio-capabilities", policy=policy)


def test_cache_miss_then_hit() -> None:
    record = capability()
    cache = InMemoryCompiledBundleCache()
    resolver = CompiledCapabilityResolver(registry(record), cache=cache)

    first = resolver.activate([record.id])
    second = resolver.activate([record.id])

    assert first.status == ActivationStatus.READY
    assert first.resolved[0].source == BundleSource.COMPILED
    assert first.metrics.compilations == 1
    assert second.resolved[0].source == BundleSource.CACHE
    assert second.metrics.cache_hits == 1
    assert cache.stats().hits == 1
    assert cache.stats().misses == 1


def test_cache_ttl_expiry_recompiles() -> None:
    clock = FakeClock()
    record = capability()
    cache = InMemoryCompiledBundleCache(clock=clock)
    resolver = CompiledCapabilityResolver(
        registry(record),
        cache=cache,
        policy=RuntimeBundlePolicy(ttl_seconds=10),
    )
    resolver.activate([record.id])
    clock.value += 11
    second = resolver.activate([record.id])
    assert second.resolved[0].source == BundleSource.COMPILED
    assert cache.stats().expirations == 1


def test_cache_is_lru_bounded() -> None:
    cache = InMemoryCompiledBundleCache(max_entries=2)
    records = [capability(f"cap.{idx}") for idx in range(3)]
    resolver = CompiledCapabilityResolver(registry(*records), cache=cache)
    resolver.activate([records[0].id])
    resolver.activate([records[1].id])
    resolver.activate([records[0].id])  # make cap.0 hottest
    resolver.activate([records[2].id])
    assert len(cache) == 2
    assert cache.stats().evictions == 1
    assert resolver.activate([records[0].id]).resolved[0].source == BundleSource.CACHE
    assert resolver.activate([records[1].id]).resolved[0].source == BundleSource.COMPILED


def test_cache_invalidation_and_clear() -> None:
    records = [capability("cap.a"), capability("cap.b")]
    cache = InMemoryCompiledBundleCache()
    resolver = CompiledCapabilityResolver(registry(*records), cache=cache)
    resolver.activate([item.id for item in records])
    assert resolver.invalidate("cap.a") == 1
    assert resolver.activate(["cap.a"]).resolved[0].source == BundleSource.COMPILED
    assert cache.clear() == 2
    assert len(cache) == 0
    assert cache.stats().invalidations == 3


def test_cache_validates_configuration_and_ttl() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        InMemoryCompiledBundleCache(max_entries=0)
    cache = InMemoryCompiledBundleCache()
    bundle = CapabilityCompiler().compile(
        capability(), registry_id="cepio-capabilities", policy=RuntimeBundlePolicy()
    )
    with pytest.raises(ValueError, match="ttl_seconds"):
        cache.put("bad", bundle, ttl_seconds=0)


def test_stats_are_returned_as_a_copy() -> None:
    cache = InMemoryCompiledBundleCache()
    cache.get("missing")
    snapshot = cache.stats()
    snapshot.misses = 99
    assert cache.stats().misses == 1


def test_content_change_same_version_forces_new_compilation() -> None:
    original = capability()
    cache = InMemoryCompiledBundleCache()
    first = CompiledCapabilityResolver(registry(original), cache=cache).activate([original.id])
    changed = capability(title="Condition to work context revised")
    second = CompiledCapabilityResolver(
        registry(changed, version="2"),
        cache=cache,
    ).activate([changed.id])
    assert first.bundles[0].source_digest != second.bundles[0].source_digest
    assert second.resolved[0].source == BundleSource.COMPILED


def test_unrelated_registry_growth_does_not_invalidate_target_bundle() -> None:
    target = capability()
    cache = InMemoryCompiledBundleCache(max_entries=32)
    first = CompiledCapabilityResolver(registry(target), cache=cache).activate([target.id])
    noise = [capability(f"noise.{idx}", title=f"Unrelated capability {idx}") for idx in range(500)]
    expanded = CompiledCapabilityResolver(
        registry(target, *noise, version="999"),
        cache=cache,
    ).activate([target.id])
    assert expanded.resolved[0].source == BundleSource.CACHE
    assert expanded.bundles[0].bundle_digest == first.bundles[0].bundle_digest
    assert len(cache) == 1


def test_activation_deduplicates_ids_preserving_first_order() -> None:
    records = [capability("cap.b"), capability("cap.a")]
    resolver = CompiledCapabilityResolver(registry(*records), cache=InMemoryCompiledBundleCache())
    result = resolver.activate(["cap.b", "cap.a", "cap.b"])
    assert [item.bundle.capability_id for item in result.resolved] == ["cap.b", "cap.a"]
    assert result.metrics.requested_bundles == 2


def test_activation_blocks_when_bundle_budget_exceeded() -> None:
    records = [capability("cap.a"), capability("cap.b")]
    resolver = CompiledCapabilityResolver(
        registry(*records),
        cache=InMemoryCompiledBundleCache(),
        policy=RuntimeBundlePolicy(max_bundles_per_activation=1),
    )
    result = resolver.activate(["cap.a", "cap.b"])
    assert result.status == ActivationStatus.BLOCKED
    assert "max_bundles_per_activation" in result.blockers[0]
    assert not result.resolved


def test_missing_capability_blocks_activation() -> None:
    resolver = CompiledCapabilityResolver(
        registry(capability()), cache=InMemoryCompiledBundleCache()
    )
    result = resolver.activate(["missing"])
    assert result.status == ActivationStatus.BLOCKED
    assert result.blockers == ["capability not found: missing"]


def test_profile_route_blocks_shared_activation() -> None:
    profile = capability("profile.cap", layer=CapabilityLayer.PROFILE)
    cache = InMemoryCompiledBundleCache()
    resolver = CompiledCapabilityResolver(registry(profile), cache=cache)
    result = resolver.activate([profile.id])
    assert result.status == ActivationStatus.BLOCKED
    assert result.metrics.rejected_profile_bundles == 1
    assert len(cache) == 0


def test_unresolved_required_route_blocks_before_activation() -> None:
    resolver = CompiledCapabilityResolver(
        registry(capability()), cache=InMemoryCompiledBundleCache()
    )
    routing = CapabilityRoutingResult(unresolved_required_capabilities={"missing.required"})
    result = resolver.activate_routes(routing)
    assert result.status == ActivationStatus.BLOCKED
    assert result.blockers == ["required capabilities unresolved: missing.required"]


def test_route_order_is_activation_order() -> None:
    records = [capability("cap.high"), capability("cap.low")]
    resolver = CompiledCapabilityResolver(registry(*records), cache=InMemoryCompiledBundleCache())
    routing = CapabilityRoutingResult(
        routes=[
            CapabilityRoute(capability_id="cap.high", score=0.9),
            CapabilityRoute(capability_id="cap.low", score=0.4),
        ]
    )
    result = resolver.activate_routes(routing)
    assert [item.bundle.capability_id for item in result.resolved] == ["cap.high", "cap.low"]


def test_cache_loss_does_not_change_bundle_semantics() -> None:
    record = capability()
    first = CompiledCapabilityResolver(
        registry(record),
        cache=InMemoryCompiledBundleCache(),
    ).activate([record.id])
    second = CompiledCapabilityResolver(
        registry(record, version="different-registry-version"),
        cache=InMemoryCompiledBundleCache(),
    ).activate([record.id])
    assert first.bundles[0] == second.bundles[0]
    assert capability_source_digest(record) == first.bundles[0].source_digest
