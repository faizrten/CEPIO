# CEPIO Compiled Industry IQ & Hot Cache v0.1

## Purpose

Phase 4 turns governed Capability Registry records into small deterministic runtime bundles that can be activated repeatedly without reconstructing the same capability contract for every request.

The governing invariant is:

> Compounding Industry IQ should reduce repeated runtime work. Cache acceleration may change latency, but it must never change CEPIO authority, policy, provenance, or semantics.

This layer sits after capability routing and before model/agent execution:

```text
RetrievalIntent
    |
    v
Capability Router
    |
    v
CapabilityRoutingResult
    |
    v
CompiledCapabilityResolver
    |
    +---- cache hit ----> immutable runtime bundle
    |
    +---- cache miss ---> CapabilityCompiler ---> hot cache
    |
    v
skills + evidence requirements + policies + authority + runtime bindings
    |
    v
bounded retrieval / ContextAssembler / reasoning
```

## Runtime bundle

A compiled bundle is a deterministic projection of a single governed `CapabilityRecord`. It retains:

- capability ID and capability version;
- layer and maturity;
- semantic terms and relationships;
- personas and competencies;
- evidence requirements and qualification evidence references;
- reasoning patterns and skills;
- decisions, policies and authority requirements;
- Industry IQ pack references;
- runtime bindings and uncertainty models;
- validated domains;
- promotion provenance;
- a canonical source digest and bundle digest.

It is immutable. Compilation does not promote maturity, grant authority, or mutate the Capability Registry.

## Capability-scoped invalidation

The cache identity is derived from:

```text
compiler version
+ registry identity
+ capability ID
+ capability version
+ canonical capability source digest
```

The registry version is intentionally *not* part of the key.

This means adding or promoting an unrelated capability does not invalidate every compiled capability. A changed capability produces a different source digest and therefore a natural cache miss.

This is a key scaling property for a compounding knowledge system.

## Shared-cache boundary

v0.1 permits shared compilation only for:

- CORE;
- COMMON;
- DOMAIN.

`PROFILE` capabilities are always rejected from the shared compiled cache, even if a caller attempts to modify policy to allow them.

Customer/profile context remains tenant-bound and is composed at request time through Memory & Context. A future tenant-specific compiled overlay requires a separate contract with tenant identity in the key and explicit lifecycle/security rules.

## Cache contract

`CompiledBundleCache` is source-neutral. CEPIO Core does not require Redis, Azure Managed Redis, an in-process cache, or any other particular product.

The v0.1 reference implementation is an in-memory, thread-safe LRU/TTL cache with:

- configurable capacity;
- TTL expiry;
- capability-level invalidation;
- clear operation;
- hit/miss/write/eviction/expiration/invalidation metrics.

A production distributed cache can replace it without changing bundle semantics.

The cache is a rebuildable acceleration projection. It is never the source of truth.

## Fail-closed activation

`CompiledCapabilityResolver` accepts explicit capability IDs or the Phase 3 `CapabilityRoutingResult`.

Activation blocks if:

- a required routed capability was unresolved;
- a routed capability no longer exists;
- requested bundles exceed the activation budget;
- a capability crosses the shared-cache boundary.

Cache loss does not block valid execution. CEPIO recompiles from the authoritative Capability Registry.

## Performance model

For a stable capability:

```text
first use:
Capability Registry -> compile -> cache -> runtime bundle

subsequent use:
Capability Registry identity + capability fingerprint -> cache -> runtime bundle
```

The runtime still verifies the current capability fingerprint before accepting a cached bundle. The cache therefore improves repeated activation without turning stale cache state into authority.

## Qualification

The dedicated Phase 4 canary proves:

1. the first activation compiles the governed target capability;
2. 100 repeated activations resolve from cache;
3. adding 500 unrelated capabilities does not invalidate the target bundle;
4. target bundle semantics/digest remain unchanged after registry growth;
5. cache pressure cannot exceed configured capacity;
6. eviction occurs under pressure;
7. profile-specific knowledge never enters shared compilation.

The target is the promoted cross-domain reliability capability:

`industrial.reliability.condition-work-context`

## Relationship to other CEPIO subsystems

### Capability Registry

Authoritative source. Compiled bundles are derived projections only.

### Retrieval & Indexing

Phase 3 chooses the relevant capability set. Phase 4 turns that set into executable runtime context efficiently.

### Memory & Context

Customer/profile memory remains outside the shared bundle and is composed into bounded working context separately.

### Skills / Workflow / Policy

The bundle carries governed references; it does not bypass their runtime qualification or authority checks.

### Compounding Intelligence

Promotion or changed capability content naturally produces a new content identity. Unrelated knowledge growth leaves existing hot bundles reusable.

## Not in v0.1

- distributed cache infrastructure;
- tenant-specific compiled profile overlays;
- precompiled model prompts;
- cached model answers;
- policy bypass based on cache state;
- automatic capability promotion;
- persistent cache snapshots;
- cache coherence across multiple runtime instances.

Those should be introduced only behind the v0.1 contracts and qualification invariants.
