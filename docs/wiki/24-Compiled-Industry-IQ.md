# Compiled Industry IQ

Compiled Industry IQ is CEPIO's Phase 4 runtime acceleration layer.

It converts governed Capability Registry records into immutable runtime bundles and reuses them through a bounded hot cache.

```text
Capability Router
      |
      v
routed capabilities
      |
      v
CompiledCapabilityResolver
      |
      +-- hit --> hot bundle
      |
      +-- miss -> deterministic compile -> cache
      |
      v
reasoning / retrieval / skills / workflow
```

## Why it exists

Industry IQ should become faster as reusable knowledge grows. Reconstructing the same capability semantics, skills, evidence requirements, policies and authority references on every request would waste work.

Phase 4 makes the reusable portion compile-once/use-many.

## Non-negotiable boundaries

- Capability Registry remains authoritative.
- Cache is acceleration only.
- Capability content changes force a new cache identity.
- Unrelated registry growth does not flush unchanged capabilities.
- CORE, COMMON and DOMAIN may use the shared cache.
- PROFILE is never allowed into the shared cache.
- Cache loss recompiles from source and cannot alter semantics.
- Activation remains explicitly bounded.

## v0.1 reference cache

The reference cache is in-memory LRU + TTL. It proves the contract without choosing production infrastructure.

A distributed cache can be added later behind the same interface.

See `docs/compiled-industry-iq.md` and ADR-0031.
