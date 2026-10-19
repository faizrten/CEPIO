# ADR-0023: Performance Contract Registry v0.1

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1

## Context

ADR-0022 introduced deterministic specialization across `industry_reference`,
`organization`, `role/persona`, and `individual` Performance Contracts. The resolver is
intentionally in-memory and accepts one definition per contract ID. That is sufficient
for semantic composition, but not for a durable Industry IQ runtime.

A production-oriented runtime needs to retain multiple immutable revisions, identify one
active revision per contract ID, resolve historical revisions reproducibly, and preserve
customer scope. Historical resolution must not drift when a parent contract later gets a
new active revision.

## Decision

CEPIO adds a versioned Performance Contract Registry with in-memory and SQLite reference
stores.

### Immutable revisions

A revision is identified by `(contract_id, version)`. Its definition payload is immutable
and fingerprinted with a deterministic SHA-256 hash. Re-registering an existing revision
fails closed.

Lifecycle metadata is separate from the immutable definition payload:

```text
draft -> active -> retired
```

Only one revision of a given contract ID may be active at a time. Activating a newer
revision retires the previous active revision. Retired revisions cannot be reactivated.

### Parent-version pinning

When a contract extends another contract, the registry stores the exact parent revision:

```text
parent_contract_id
parent_version
parent_definition_hash
```

If `parent_version` is omitted at registration time, the currently active parent revision
is pinned. If no active parent exists, registration fails closed.

Resolution follows these immutable pins rather than re-selecting whichever parent happens
to be active later. This guarantees that historical organization, role/persona and
individual contracts remain reproducible after reference or enterprise contracts evolve.

A missing pinned parent or hash mismatch fails closed.

### Effective organization scope

Every stored revision records the effective organization ID produced by resolving the
full specialization chain. This means a sparse role or individual overlay that does not
repeat `organization_id` is still persisted with its effective customer scope.

Industry-reference revisions remain organization-neutral. Registry resolution can assert
an expected organization ID and rejects mismatches.

This is a persistence and retrieval boundary, not an authorization substitute. Future
REST/MCP surfaces must still apply CEPIO identity and policy controls.

### Resolution provenance

Registry-backed resolution returns both:

1. the existing fully resolved `PerformanceContract` and element-level lineage; and
2. the ordered immutable revision references `(contract_id, version, definition_hash)`
   used to produce it.

This provides a stable audit anchor for future formula execution, API responses and
workflow recommendations.

### Storage contract

`InMemoryPerformanceContractStore` provides deterministic local/test behavior.
`SQLitePerformanceContractStore` is the durable reference implementation.

The registry owns lifecycle and semantic rules; storage backends own persistence.
Additional enterprise backends can implement the same store protocol without changing
Performance Contract semantics.

## Consequences

### Positive

- Historical performance meaning remains reproducible after parent revisions change.
- Customer scope is explicit even for sparse descendant overlays.
- One active revision per contract ID removes ambiguous runtime selection.
- Draft and retired revisions remain available for audit and historical replay.
- Formula execution and API/MCP surfaces can now bind to immutable contract revisions.
- SQLite provides an immediately usable durable DEV/reference backend.

### Trade-offs

- Parent versions are intentionally pinned, so adopting a newer parent requires a new
  child revision rather than silently changing effective meaning.
- Retired revisions are terminal in v0.1.
- The registry does not yet implement distributed locking or a cloud-native database
  backend.

## Non-goals

This ADR does not introduce:

- formula or Business Logic execution;
- REST/MCP performance endpoints;
- workflow auto-start;
- field-level overlay patches or tombstones;
- quantitative causal inference;
- cross-customer inheritance.

## Validation

Tests cover:

- durable SQLite round-trip and reopen;
- exact parent-version pinning;
- historical resolution after parent supersession;
- one-active-version lifecycle;
- terminal retirement;
- explicit and implicit parent selection;
- organization-scoped listing and resolution;
- missing/tampered pinned parents;
- inheritance cycles;
- duplicate revisions; and
- registry translation of semantic resolution failures.
