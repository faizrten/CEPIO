# CEPIO Codex Engineering Brief — v0.4

## Mission

Build CEPIO into an operational ontology platform for Energy & Process Industries with parity-oriented capabilities against Palantir Ontology while remaining Microsoft/Fabric-native and source-system-neutral.

## Current baseline: v0.3

Do not regress these capabilities:

- canonical modular CEPIO domain architecture;
- SEO/SATORP and AD/ARO normalization rules;
- IRI-first identity for classes, relationships and datatype properties;
- ambiguity fail-closed behavior;
- semantic module versions, dependencies and compatibility snapshots;
- canonical datatype-property registry with semantic/write authority;
- property-level provenance, source references and transformation runs;
- `explain_property(...)` lineage path;
- immutable object-version history;
- bitemporal object and relationship queries;
- deterministic event ordering and projector contract;
- compressor operating-state reference projector;
- independent projection checkpoints and replay;
- SQLite + in-memory reference persistence;
- optimistic concurrency;
- immutable action audit;
- policy evaluated before idempotent replay;
- actor/action/target-scoped idempotency;
- action preconditions and approval metadata;
- AI recommend-but-not-execute boundary;
- typed functions;
- graph traversal including inverse paths;
- MCP-ready governed facade;
- thin Python SDK;
- dry-run external adapter contracts;
- SHACL validation path;
- all tests passing.

## Documentation policy

Documentation is part of the product contract, not an afterthought.

Any PR that changes a user-visible or developer-visible CEPIO capability MUST update the corresponding documentation in the same PR, or explicitly state why there is no documentation impact.

Changes that normally require documentation updates include:

- ontology modules, classes, properties, relationships or profiles;
- API, SDK, CLI, MCP tools or query behavior;
- runtime architecture, persistence, policy, action or decision behavior;
- source-system adapters and platform integrations;
- deployment, identity, security, observability or governance behavior;
- compatibility, migration or versioning rules;
- supported standards and federation mappings;
- reference applications, examples, scenarios or release status;
- roadmap milestones when implementation status changes.

Documentation hierarchy:

1. implementation contracts, code, ontology files, mappings, shapes and focused technical docs are authoritative;
2. `docs/wiki/` is the explanatory and navigation layer and must accurately reflect those contracts;
3. `README.md` and `docs/README.md` provide repository-level orientation and must remain consistent with the wiki.

A feature is not complete when its implementation lands but its public explanation remains stale.

## Next sprint: v0.4 — Operational Query + Platform Integration

### P0 — Typed temporal query contract

- Implement a backend-neutral query model for object type, property predicates, relationships and time.
- Support transaction-time and valid-time filters explicitly.
- Support bounded graph traversal without introducing a proprietary query language.
- Add deterministic pagination and ordering.
- Expose the query contract through Python SDK, REST and MCP.

### P0 — Ontology migration manifests

- Define explicit migration manifests for intentional class/property/relationship changes.
- Support rename, replacement/deprecation and compatible datatype transformations.
- Require breaking semantic-contract changes to include an approved migration declaration.
- Add CI validation for migration coverage.
- Keep migration execution deterministic and auditable.

### P1 — Projection provenance and causal state

- Link each derived projected property to the source event IDs that produced it.
- Add projector version and replay/run IDs to provenance.
- Support multi-object projections without mutating source events.
- Add causal lineage from Event → State → Decision → Action.

### P1 — Runtime observability

- Emit structured runtime telemetry for repository latency, query execution, function invocation, policy decision, action execution and projection rebuild.
- Add an OpenTelemetry-compatible hook interface without forcing one exporter/backend.
- Ensure telemetry cannot leak properties the actor was not authorized to read.

### P1 — Event ingestion contracts

- Define source-neutral event-ingestion adapter contracts.
- Add dry-run/reference adapters for Fabric Real-Time Intelligence / Eventstreams and AVEVA PI.
- Require idempotent ingestion keys and event-time preservation.
- Preserve source references and ingestion provenance.

### P1 — Microsoft platform mapping

Add explicit mapping contracts for:

- OneLake / Fabric data stores;
- Fabric IQ / Ontology / Graph;
- Fabric Real-Time Intelligence;
- Microsoft Purview lineage/governance;
- Entra identity/policy boundaries;
- Microsoft Foundry agents;
- Copilot Studio;
- Power Automate / governed action adapters.

Keep Microsoft-specific mappings outside CEPIO-Core/domain ontology semantics.

### P2 — Agent-facing temporal tools

Add MCP tools such as:

- `cepio_get_object_at`;
- `cepio_get_object_valid_at`;
- `cepio_query`;
- `cepio_explain_property`;
- `cepio_explain_state`;
- `cepio_rebuild_projection` with governed authorization.

Agents must receive only authorized temporal/property views.

## Security invariants

1. Policy evaluation precedes every external side effect and idempotent replay.
2. Agents receive only authorized objects, properties and tools.
3. Human approval cannot be represented by an AI role claiming a string flag.
4. Audit and historical records remain append-only through ordinary APIs.
5. Provenance must not be writable by ordinary domain action handlers.
6. Adapter failures must reconcile explicitly; never infer external success from local CEPIO success.
7. Temporal/history queries must enforce the same property/object authorization as current-state queries.
8. Observability and lineage outputs must not bypass authorization controls.
9. Projection rebuilds may alter derived state only; they must never mutate source events.
10. Breaking ontology changes must fail CI without a migration declaration.

## Definition of done for v0.4

- all v0.3 tests pass;
- query contract supports type/property/relationship + transaction/valid-time filtering;
- REST, SDK and MCP expose the same query semantics;
- deliberate breaking ontology change is rejected without a migration manifest;
- projection provenance identifies source event IDs and projector version;
- event ingestion is deterministic/idempotent in reference adapters;
- OpenTelemetry-compatible hooks exist and are authorization-safe;
- Microsoft mapping contracts are documented/testable without contaminating CEPIO-Core;
- no live production side effect is introduced unless explicitly opt-in and policy-gated;
- relevant `docs/wiki/` pages and focused technical documentation are updated in the same PR for every material capability change, or the PR explicitly documents why there is no documentation impact.
