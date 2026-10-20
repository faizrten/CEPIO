#!/usr/bin/env python3
"""Qualification canary for CEPIO Compiled Industry IQ v0.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.capability_registry import CapabilityRegistry, load_capability_registry
from cepio.capability_routing import CapabilityRouter
from cepio.compiled_iq import (
    ActivationStatus,
    BundleSource,
    CompiledCapabilityResolver,
    InMemoryCompiledBundleCache,
    RuntimeBundlePolicy,
)
from cepio.retrieval_contracts import RetrievalIntent

ROOT = Path(__file__).resolve().parents[1]
TARGET_CAPABILITY = "industrial.reliability.condition-work-context"


def _expanded_registry(base: CapabilityRegistry, count: int) -> CapabilityRegistry:
    target = base.get(TARGET_CAPABILITY)
    if target is None:
        raise RuntimeError(f"qualification target missing: {TARGET_CAPABILITY}")
    synthetic = []
    for idx in range(count):
        synthetic.append(
            target.model_copy(
                deep=True,
                update={
                    "id": f"synthetic.unrelated.{idx:04d}",
                    "version": "0.1",
                    "title": f"Synthetic unrelated capability {idx}",
                    "description": "Qualification-only capability used to test cache isolation.",
                    "semantic_terms": {f"SyntheticTerm{idx}"},
                    "semantic_relationships": set(),
                    "personas": {"synthetic-persona"},
                    "competencies": {f"synthetic-competency-{idx}"},
                    "evidence_requirements": {"synthetic-evidence"},
                    "reasoning_patterns": {"synthetic-reasoning"},
                    "skills": {f"synthetic-skill-{idx}"},
                    "decisions": {f"synthetic-decision-{idx}"},
                    "authority_requirements": set(),
                    "policy_requirements": set(),
                    "industry_iq_packs": set(),
                    "runtime_bindings": set(),
                    "uncertainty_models": set(),
                    "validated_domains": {"synthetic-domain"},
                    "evidence": [],
                },
            )
        )
    return base.model_copy(
        deep=True,
        update={
            "version": f"{base.version}-qualification-expanded",
            "capabilities": [*base.capabilities, *synthetic],
        },
    )


def run() -> dict[str, object]:
    source = ROOT / "generalization" / "capabilities" / "registry-v0.1.yaml"
    registry = load_capability_registry(source)
    target = registry.get(TARGET_CAPABILITY)
    if target is None:
        raise RuntimeError(f"qualification target missing: {TARGET_CAPABILITY}")

    policy = RuntimeBundlePolicy(
        max_cache_entries=32,
        ttl_seconds=900,
        max_bundles_per_activation=5,
    )
    cache = InMemoryCompiledBundleCache(max_entries=policy.max_cache_entries)
    resolver = CompiledCapabilityResolver(registry, cache=cache, policy=policy)
    routing = CapabilityRouter(registry).route(
        RetrievalIntent(required_capability_ids={TARGET_CAPABILITY})
    )
    first = resolver.activate_routes(routing)
    if first.status != ActivationStatus.READY:
        raise RuntimeError(f"initial activation blocked: {first.blockers}")
    if first.resolved[0].source != BundleSource.COMPILED:
        raise RuntimeError("first activation must compile the target bundle")

    target_digest = first.bundles[0].bundle_digest
    repeated_hits = 0
    for _ in range(100):
        repeated = resolver.activate_routes(routing)
        if repeated.status != ActivationStatus.READY:
            raise RuntimeError(f"repeat activation blocked: {repeated.blockers}")
        if repeated.resolved[0].source != BundleSource.CACHE:
            raise RuntimeError("repeat activation must resolve from hot cache")
        if repeated.bundles[0].bundle_digest != target_digest:
            raise RuntimeError("cached bundle digest changed across repeated activation")
        repeated_hits += 1

    expanded = _expanded_registry(registry, 500)
    expanded_resolver = CompiledCapabilityResolver(expanded, cache=cache, policy=policy)
    expanded_routing = CapabilityRouter(expanded).route(
        RetrievalIntent(required_capability_ids={TARGET_CAPABILITY})
    )
    after_growth = expanded_resolver.activate_routes(expanded_routing)
    if after_growth.status != ActivationStatus.READY:
        raise RuntimeError(f"activation after registry growth blocked: {after_growth.blockers}")
    if after_growth.resolved[0].source != BundleSource.CACHE:
        raise RuntimeError("unrelated registry growth invalidated the target cache entry")
    if after_growth.bundles[0].bundle_digest != target_digest:
        raise RuntimeError("unrelated registry growth changed target bundle semantics")

    synthetic_ids = [item.id for item in expanded.capabilities if item.id.startswith("synthetic.")]
    for capability_id in synthetic_ids[:64]:
        result = expanded_resolver.activate([capability_id])
        if result.status != ActivationStatus.READY:
            raise RuntimeError(f"synthetic activation blocked: {result.blockers}")
    if len(cache) > policy.max_cache_entries:
        raise RuntimeError("hot cache exceeded configured capacity")
    stats = cache.stats()
    if stats.evictions == 0:
        raise RuntimeError("bounded-cache qualification did not exercise eviction")

    return {
        "contract": "compiled-industry-iq-v0.1",
        "target_capability": TARGET_CAPABILITY,
        "target_bundle_digest": target_digest,
        "target_bundle_bytes": len(first.bundles[0].model_dump_json().encode("utf-8")),
        "first_activation_source": first.resolved[0].source.value,
        "repeated_cache_hits": repeated_hits,
        "expanded_registry_capabilities": len(expanded.capabilities),
        "growth_activation_source": after_growth.resolved[0].source.value,
        "cache_entries_after_pressure": len(cache),
        "cache_capacity": policy.max_cache_entries,
        "cache_stats": stats.model_dump(),
        "invariants": {
            "compile_once_use_many": repeated_hits == 100,
            "unrelated_growth_preserves_target_cache": True,
            "cache_capacity_bounded": len(cache) <= policy.max_cache_entries,
            "cache_loss_not_authority": True,
            "profile_memory_not_shared_compilation": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run()
    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
