# CEPIO v0.4 FOUNDATION — Developer Preview Release Manifest

Release: **0.4.0 — Developer Preview**

## Product claim

CEPIO v0.4 FOUNDATION qualifies a coherent Microsoft-native, source-system-neutral industrial semantic + kinetic developer/runtime contract that can be consumed through a versioned public API, Entra-authenticated policy boundary, reference Microsoft hosting profiles, Fabric/Fabric IQ bindings and Foundry/MCP integration contracts.

This release is a **Developer Preview**. It does not claim enterprise production HA, production-distributed persistence, live industrial-system writeback, current hosted Management/MCP productization, or every capability subsequently merged to repository `main`.

> **Important:** repository `main` has advanced materially beyond the v0.4 release guarantee. Later mainline implementation does not retroactively expand this release manifest. See [`docs/current-state.md`](docs/current-state.md) for the dated repository snapshot.

## North-Star context

Current product positioning is:

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

v0.4 FOUNDATION is the qualified foundation beneath that direction. Palantir Ontology is a capability benchmark rather than CEPIO's product identity.

## Supported Developer Preview surface

### Canonical runtime

- canonical Energy & Process Industry ontology modules and first-class customer profiles;
- IRI-first semantic identity, relationship validation and canonical property contract;
- immutable provenance and temporal/history capabilities established in v0.3;
- deterministic event/state projection;
- typed Functions, Decisions, governed Actions, preconditions, audit and scoped idempotency.

### Public API v1

- supported public namespace under `/api/v1`;
- committed `openapi/cepio-v1.yaml` baseline;
- 18 route/method/operation-ID contracts checked in CI at the v0.4 qualification boundary;
- actor-scoped reads and typed queries;
- standardized public error envelope and `X-Request-ID` correlation;
- object `ETag` and `If-Match` optimistic concurrency;
- Action `Idempotency-Key` semantics;
- cursor pagination and query-budget errors.

The v0.4 OpenAPI compatibility gate is intentionally **route-contract based plus selected product-critical semantics**. Full request/response schema compatibility generation is not a v0.4 guarantee.

### Clients

- Python `CEPIOClient` shipped in the wheel and aligned to `/api/v1`;
- TypeScript reference client source in `clients/typescript/cepio.ts`;
- CI validation of both client operation maps against the accepted OpenAPI route contract.

The TypeScript client is reference source in v0.4; it is not a v0.4 guarantee of a published npm package or fully generated SDK.

### Security

- Microsoft Entra token signature, issuer, audience and lifetime validation for production mode;
- caller identity derived from token claims rather than request-supplied authority;
- explicit development-auth mode that fails closed in production configuration;
- object type, sharing-scope, property, Function and Action policy controls;
- authorization applied before exposed query counts, sorting, cursor positions and page results;
- spoofed Action identity attempts rejected and audited.

### Query execution

- repository-level typed-query execution for the SQLite reference backend;
- deterministic opaque cursor pagination;
- conservative SQL pushdown with semantic revalidation;
- configured query complexity/execution budgets;
- in-memory/SQLite semantic parity tests;
- repeatable 5,000-object CI regression baseline.

### Microsoft platform bindings

At the v0.4 qualification boundary:

- Fabric/Fabric IQ semantic binding contracts;
- Foundry/MCP actor-scoped query/Function/Action integration contract;
- App Service reference deployment profile;
- AKS reference deployment profile;
- one portable CEPIO container contract across reference hosts.

Later mainline work has since advanced Fabric live-proof, hosted MCP, Management and Foundry qualification paths. Those later capabilities are documented in `docs/current-state.md` and their focused contracts; they are not retroactive v0.4 guarantees.

### Observability

- backend-neutral telemetry sink/event contract;
- repository, policy, Function and Action duration/success/failure telemetry;
- sanitized rejected-Action telemetry;
- optional OpenTelemetry adapter without a mandatory OpenTelemetry Core dependency;
- adapter telemetry boundary for future live connectors.

## Release qualification

The v0.4 gate required successful CI for:

- full pytest suite;
- SHACL validation;
- public API v1 contract check;
- Python/TypeScript route-contract validation;
- ontology compatibility gate;
- deployment-profile validation;
- cross-domain reasoning demo;
- SQLite typed-query load regression;
- clean wheel build and install outside the source checkout;
- clean container build, startup and `/api/v1/health` check.

The final qualifying CI run for the release PR remains the authoritative evidence for test count and release-gate success.

## Reference query baseline

A pre-release CI reference run on 2026-10-15 queried 5,000 SQLite-backed compressor objects in **6.306 ms** for the configured regression case, returned a 100-object page, and explicitly prohibited fallback through `runtime.list_objects()`.

This is a regression reference, not a production SLO. See `docs/query-load-baseline.md`.

## Experimental / reference-only surfaces at the v0.4 boundary

The following were useful for development/evaluation but were not v0.4 production guarantees:

- SQLite persistence beyond the documented single-writer reference topology;
- legacy unversioned REST routes retained temporarily for compatibility;
- full-schema OpenAPI-generated client compatibility beyond the checked route contract;
- TypeScript packaging/npm distribution;
- graph analytics at enterprise distributed-graph scale;
- Fabric/Fabric IQ and Foundry integration behavior outside documented CEPIO contracts;
- customer-profile content beyond its declared profile/module version;
- application-specific UI/workspaces.

## Outside the v0.4 guarantee

At release qualification, these capabilities were deferred beyond v0.4. Some now have partial or substantial mainline implementation, but remain outside the historical v0.4 release guarantee:

- live SAP S/4HANA and AVEVA PI qualification;
- live OSDU/P6 qualification as required by release proofs;
- governed external writeback, verification and reconciliation;
- source-neutral binding/onboarding productization;
- durable first-class workflow orchestration;
- Skill admission/execution and application-contract convergence;
- Capability Registry / Compounding Intelligence;
- Industry IQ pack trust/supply-chain controls;
- Memory / Retrieval / Compiled Industry IQ;
- Enterprise Performance Contracts/reference packs;
- hosted Management and MCP productization;
- production HA/distributed persistence;
- queues/workers/DLQ/circuit-breaker/backpressure program;
- formal production SLO/error budgets and disaster recovery qualification;
- Purview governance/lineage bridge (#20);
- GPU/cuGraph production qualification (#25).

For current mainline status, use `docs/current-state.md` rather than interpreting this historical release boundary as current implementation status.

## Known v0.4 deployment limits

1. SQLite is a single-writer reference backend and must not be horizontally scaled as a shared production data plane.
2. The supplied v0.4 AKS SQLite profile therefore used one replica and `ReadWriteOnce` storage.
3. App Service/AKS manifests were reproducible reference profiles; target landing-zone networking, secrets, private endpoints, monitoring and production repository services remained environment concerns.
4. External industrial source adapters were dry-run/reference contracts at the v0.4 release boundary.
5. Enterprise production security review, penetration testing, HA, DR and SLO qualification were not claimed by this Developer Preview.

## Documentation entry points

- `docs/current-state.md` — current repository/mainline snapshot;
- `docs/developer-preview.md` — v0.4 clean-environment qualification guide;
- `docs/rest-security.md` — Entra and authorization boundary;
- `docs/api-client-guide.md` — Python and TypeScript clients;
- `docs/api-reliability.md` — errors, request IDs, ETag/If-Match and idempotency;
- `docs/api-examples.md` — representative v1 requests;
- `docs/query-contract.md` — typed-query and cursor semantics;
- `docs/query-load-baseline.md` — measured reference regression;
- `docs/deployment-profiles.md` — reference deployment profiles;
- `docs/observability.md` — telemetry/OpenTelemetry integration;
- `docs/roadmap.md` — product release roadmap;
- `docs/wiki/Home.md` — current narrative navigation.

## Next product release

**CEPIO v0.5 CONNECT — Live Industrial Integration** moves from foundation/platform qualification to real industrial connectivity and governed external action proof.

The release gate requires provenance-backed multi-source context, live source qualification (especially SAP/PI), identity reconciliation, governed writeback, read-back/verification/reconciliation and the K-201 compressor reference scenario across at least three authoritative source domains.
