# ADR-0031: Compiled Industry IQ and shared hot-cache boundary v0.1

- Status: Accepted
- Date: 2026-10-20
- Decision owners: CEPIO architecture
- Scope: CEPIO Core runtime

## Context

Memory & Context v0.1 bounded the model working set. Retrieval & Indexing v0.1 added governed capability routing and bounded evidence retrieval.

Without another layer, the runtime would still repeatedly reconstruct the same reusable capability contract—semantics, competency, evidence requirements, skills, policies, authority, runtime bindings and uncertainty references—on every request.

A compounding knowledge system must not make all existing runtime work more expensive whenever the registry grows.

## Decision

CEPIO will compile reusable Capability Registry records into immutable `CompiledCapabilityBundle` projections and may cache those projections behind a source-neutral `CompiledBundleCache` interface.

The authoritative source remains the Capability Registry.

The shared cache identity is capability-scoped and content-addressed. It includes compiler version, registry identity, capability ID/version and canonical capability source digest. It intentionally excludes registry version so unrelated registry changes do not cause global cache invalidation.

Shared compilation is permitted only for CORE, COMMON and DOMAIN capabilities.

PROFILE capabilities are prohibited from the shared cache as a hard compiler boundary, not merely a configurable default.

The reference backend is an in-memory, bounded LRU/TTL cache. No distributed cache product is required by CEPIO Core.

## Consequences

Positive:

- repeated activation can resolve from a small hot bundle;
- unrelated Industry IQ growth does not invalidate stable capabilities;
- cache loss is semantically harmless;
- capability changes invalidate themselves naturally;
- physical cache infrastructure remains replaceable;
- customer/profile knowledge remains isolated from global/shared runtime acceleration.

Trade-offs:

- a runtime instance still fingerprints the authoritative capability before accepting a hit;
- profile overlays remain request-time work in v0.1;
- multi-instance distributed cache coherence is deferred;
- a changed capability can coexist briefly with its prior cached entry until TTL/LRU/invalidation removes it.

## Rejected alternatives

### Key cache entries by entire registry version

Rejected. Any new unrelated capability would invalidate every hot bundle and make compounding knowledge create global cache churn.

### Cache fully assembled customer context

Rejected for v0.1. It increases cross-tenant leakage risk and couples global capability acceleration to customer-specific lifecycle rules.

### Cache model answers

Rejected. Phase 4 caches governed capability contracts, not conclusions or generated responses.

### Require Redis or a cloud cache in CEPIO Core

Rejected. Cache infrastructure is a deployment adapter, not an Industry IQ semantic dependency.

## Qualification

Merge requires:

- deterministic bundle compilation;
- hard PROFILE boundary;
- compile-once/use-many proof;
- content-change invalidation;
- unrelated-registry-growth reuse proof;
- bounded LRU/TTL behavior;
- Phase 3 routing integration;
- no coverage-debt regression;
- standard Governance, CI, CodeQL and Quality Gate success.
