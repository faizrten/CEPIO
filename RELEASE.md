# CEPIO v0.3 Release Manifest

Release: **0.3.0 — Temporal + Provenance Kernel**

## Release scope

v0.3 promotes CEPIO from a v0.2 operational runtime into a versioned industrial semantic contract with provenance, bitemporal history and deterministic state reconstruction.

### Domain normalization

- Canonical industrial-common modules for Asset, Work Management, Reliability, HSE, Supply, Performance, Workforce and Agentic Operations.
- Domain/enterprise modules for Process Industry, EPCIC, Drilling and Commercial semantics.
- 42/42 SEO refinery/petrochemical/EPC entities mapped.
- 59/59 AD drilling/asset-heavy core entities mapped.
- 967 SEO/AD source-property occurrences classified.
- Customer-specific concepts remain profile semantics instead of polluting CEPIO common modules.

### Semantic contract

- Full RDF IRI is canonical identity for classes, object relationships and datatype properties.
- Local/QName aliases resolve only when unambiguous.
- Ontology modules declare namespace, semantic version, tier, stability and dependencies.
- Compatibility snapshots detect breaking class/property/relationship removals and range changes.
- Canonical datatype properties declare datatype and semantic/write authority.

### Provenance

- `SourceReference`.
- `TransformationRun`.
- `PropertyProvenance`.
- Source-value hashing without persisting raw source values.
- In-memory and SQLite provenance repositories.
- `explain_property(...)` lineage explanation path for applications and agents.

### Temporal history

- Immutable object-version snapshots.
- `get_object_at(id, transaction_time)` transaction-time reconstruction.
- `get_object_valid_at(id, valid_time, as_of_transaction=...)` bitemporal object queries.
- Immutable relationship revision history.
- `relationships_at(..., as_of_transaction=...)` bitemporal graph queries.
- Explicit transaction-time vs valid-time semantics.
- Retroactive corrections append history instead of overwriting it.

### Deterministic state projection

- Stable event ordering by `(occurred_at, event_id)`.
- Projector interface for immutable events → derived ontology state.
- Reference compressor operating-state projector.
- Projection checkpoints stored separately from source events.
- State hash, projector/version, event count, last event and rebuild timestamp persisted.
- Derived state can be deleted and rebuilt from immutable event history.

## Verification

Validated in GitHub Actions on Python 3.11:

- **36 pytest tests pass**.
- SHACL validation conforms with pySHACL.
- Existing refinery cross-domain demo executes end-to-end.
- SQLite object/provenance/history/projection persistence survives restart.
- Optimistic concurrency still rejects stale writes.
- Existing action, policy, idempotency, audit, function and MCP security invariants remain intact.

## Security and governance invariants

1. Historical snapshots are not mutable through ordinary domain APIs.
2. Source events are immutable; projections are disposable/rebuildable derived state.
3. Policy evaluation still precedes governed external side effects and idempotent replay.
4. AI recommenders cannot cross execution boundaries without authorized identity/policy.
5. Provenance is separate from ordinary domain mutation authority.
6. Ambiguous semantic aliases fail closed.

## Known limits

- SQLite is a reference backend, not the target production distributed graph store.
- Projection checkpoint persistence and ontology state updates are recoverable through replay but are not yet a distributed transaction.
- External adapters remain dry-run only; no live SAP/PI/OSDU writeback is enabled.
- Temporal filtering is not yet exposed through the full typed query/MCP surface.
- Ontology breaking changes are detectable, but intentional migration-manifest execution is a follow-on.
- OpenTelemetry/runtime observability hooks are not yet implemented.

## Next release

v0.4 targets the **Operational Query + Platform Integration** layer:

- typed temporal/relationship/property query contract;
- ontology migration manifests and CI migration gates;
- OpenTelemetry-compatible runtime observability;
- projection provenance and multi-object causal projections;
- explicit Fabric / Fabric IQ / Purview / Foundry / Entra mapping contracts;
- event-ingestion adapters for Fabric Real-Time Intelligence / Eventstreams and AVEVA PI;
- richer MCP tools for time-travel, lineage and governed industrial reasoning.
