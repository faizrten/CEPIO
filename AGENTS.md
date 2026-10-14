# CEPIO Codex Engineering Brief — v0.3

## Mission

Build CEPIO into an operational ontology platform for Energy & Process Industries with parity-oriented capabilities against Palantir Ontology while remaining Microsoft/Fabric-native and source-system-neutral.

## Current baseline: v0.2

Do not regress these capabilities:

- object/relationship/event/decision repository contracts;
- SQLite + in-memory implementations;
- optimistic concurrency;
- immutable action audit;
- policy evaluated before idempotent replay;
- actor/action/target-scoped idempotency;
- RDF type registry and relationship domain/range validation;
- action preconditions and approval metadata;
- object/property/action authorization;
- AI recommend-but-not-execute boundary;
- typed functions;
- graph traversal including inverse paths;
- MCP-ready facade;
- thin Python SDK;
- dry-run adapter contracts;
- SHACL validation path;
- all tests passing.

## Next sprint: v0.3 — Temporal + Provenance Kernel

### P0 — Version history
- Add immutable object-version snapshots.
- Support `get_object_at(object_id, timestamp)`.
- Add relationship version/valid-time history.
- Never overwrite historical versions.

### P0 — Provenance
- Define `SourceReference`, `PropertyProvenance`, `TransformationRun` and `LineageEdge`.
- Attach source system + external ID + ingestion timestamp to object/property mutations.
- Allow applications/agents to ask why a property has its current value.

### P0 — State projection
- Create projector interface from event stream → current object state.
- Make projections deterministic and replayable.
- Add compressor operating-state reference projector.

### P1 — Ontology lifecycle
- Add semantic module manifests with version and dependencies.
- Add compatibility checker for removed/renamed classes, relationships and constraints.
- Add migration manifest format and CI gate.

### P1 — Query
- Add query/filter contract for object type, properties, relationships and time.
- Avoid introducing a CEPIO-specific query language until requirements prove it necessary.

### P1 — Observability
- Add structured runtime events for function invocation, policy decision, action and repository latency.
- Add OpenTelemetry-compatible hook interface without forcing one backend.

### P2 — Microsoft mapping
- Add explicit architecture notes and mapping contracts for Fabric/OneLake/Fabric IQ/Purview/Entra/Foundry/Copilot Studio.
- Keep these mappings outside CEPIO-Core abstractions.

## Security invariants

1. Policy evaluation precedes every external side effect and idempotent replay.
2. Agents receive only authorized objects/properties/tools.
3. Human approval cannot be represented by an AI role claiming a string flag.
4. Audit is append-only.
5. Provenance must not be writable by ordinary domain action handlers.
6. Adapter failures must reconcile explicitly; never infer external success from local CEPIO success.

## Definition of done for v0.3

- all v0.2 tests pass;
- new temporal/provenance tests pass;
- object state can be reconstructed at time T;
- each demo property can identify its source reference;
- an event stream can deterministically rebuild compressor state;
- ontology breaking changes fail CI unless accompanied by a migration declaration;
- no live production side effect is introduced.
