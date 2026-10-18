# CEPIO v0.4 FOUNDATION — Developer Preview Release Manifest

Release: **0.4.0 — FOUNDATION / Developer Preview**

## Product claim

CEPIO v0.4 **FOUNDATION** establishes a coherent developer/runtime contract for the CEPIO industrial operating intelligence layer. It is source-system-neutral and can be consumed through a versioned public API, Entra-authenticated policy boundary, reference Microsoft hosting profiles, Fabric/Fabric IQ bindings and Foundry/MCP integration.

This release is a **Developer Preview**. `FOUNDATION` is the roadmap capability label: it means developers can build against a coherent CEPIO operating contract. It does not claim enterprise production HA, production-distributed persistence or live industrial-system writeback.

## Supported Developer Preview surface

### Canonical runtime

- canonical Energy & Process Industry ontology modules and first-class customer profiles;
- IRI-first semantic identity, relationship validation and canonical property contract;
- immutable provenance and temporal/history capabilities established in v0.3;
- deterministic event/state projection;
- typed functions, Decisions, governed Actions, preconditions, audit and scoped idempotency.

### Public API v1

- supported public namespace under `/api/v1`;
- committed `openapi/cepio-v1.yaml` baseline;
- 18 route/method/operation-ID contracts checked in CI;
- actor-scoped reads and typed queries;
- standardized public error envelope and `X-Request-ID` correlation;
- object `ETag` and `If-Match` optimistic concurrency;
- action `Idempotency-Key` semantics;
- cursor pagination and query-budget errors.

The v0.4 OpenAPI compatibility gate is intentionally **route-contract based plus selected product-critical semantics**. Full request/response schema compatibility generation is not yet a v0.4 guarantee.

### Clients

- Python `CEPIOClient` shipped in the wheel and aligned to `/api/v1`;
- TypeScript reference client source in `clients/typescript/cepio.ts`;
- CI validation of both client operation maps against the accepted OpenAPI route contract.

The TypeScript client is reference source in v0.4; it is not yet a published npm package or fully generated SDK.

### Security

- Microsoft Entra token signature, issuer, audience and lifetime validation for production mode;
- caller identity derived from token claims rather than request-supplied authority;
- explicit development-auth mode that fails closed in production configuration;
- object type, sharing-scope, property, function and action policy controls;
- authorization applied before exposed query counts, sorting, cursor positions and page results;
- spoofed action identity attempts rejected and audited.

### Query execution

- repository-level typed-query execution for the SQLite reference backend;
- deterministic opaque cursor pagination;
- conservative SQL pushdown with semantic revalidation;
- configured query complexity/execution budgets;
- in-memory/SQLite semantic parity tests;
- repeatable 5,000-object CI regression baseline.

### Microsoft platform bindings

- Fabric/Fabric IQ semantic binding contracts;
- Foundry/MCP actor-scoped query/function/action integration;
- App Service reference deployment profile;
- AKS reference deployment profile;
- one portable CEPIO container contract across reference hosts.

### Observability

- backend-neutral telemetry sink/event contract;
- repository, policy, function and action duration/success/failure telemetry;
- sanitized rejected-action telemetry;
- optional OpenTelemetry adapter without a mandatory OpenTelemetry core dependency;
- adapter telemetry boundary for future live connectors.

## Release qualification

The v0.4 FOUNDATION gate requires successful CI for:

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

The final qualifying CI run for this release PR is the authoritative evidence for test count and release-gate success.

## Reference query baseline

A pre-release CI reference run on 2026-10-15 queried 5,000 SQLite-backed compressor objects in **6.306 ms** for the configured regression case, returned a 100-object page, and explicitly prohibited fallback through `runtime.list_objects()`.

This is a regression reference, not a production SLO. See `docs/query-load-baseline.md`.

## Experimental / reference-only surfaces

The following are useful for development and evaluation but are not production guarantees in v0.4:

- SQLite persistence beyond the documented single-writer reference topology;
- legacy unversioned REST routes retained temporarily for compatibility;
- full-schema OpenAPI-generated client compatibility beyond the checked route contract;
- TypeScript packaging/npm distribution;
- graph analytics at enterprise distributed-graph scale;
- Fabric/Fabric IQ and Foundry integration behavior outside the documented CEPIO contracts;
- customer-profile content beyond its declared profile/module version;
- application-specific UI/workspaces.

## Deferred beyond v0.4 FOUNDATION

- live SAP S/4HANA, AVEVA PI, OSDU and Primavera P6 adapters;
- governed external writeback, verification and reconciliation;
- source-neutral extractor/onboarding runtime;
- full production HA/distributed persistence;
- queue workers, DLQ/circuit-breaker/backpressure program;
- formal production SLO/error budgets and disaster recovery qualification;
- first-class long-running kinetic workflow orchestration (#67);
- Purview governance/lineage bridge (#20);
- GPU/cuGraph production qualification (#25).

## Known deployment limits

1. SQLite is a single-writer reference backend and must not be horizontally scaled as a shared production data plane.
2. The supplied AKS SQLite profile therefore uses one replica and `ReadWriteOnce` storage.
3. App Service/AKS manifests are reproducible reference profiles; target landing-zone networking, secrets, private endpoints, monitoring and production repository services remain environment concerns.
4. External industrial source adapters are dry-run/reference contracts until **v0.5 CONNECT** live-integration work lands.
5. Enterprise production security review, penetration testing, HA, DR and SLO qualification are not claimed by this Developer Preview.

## Documentation entry points

- `docs/developer-preview.md` — clean-environment qualification guide;
- `docs/rest-security.md` — Entra and authorization boundary;
- `docs/api-client-guide.md` — Python and TypeScript clients;
- `docs/api-reliability.md` — errors, request IDs, ETag/If-Match and idempotency;
- `docs/api-examples.md` — representative v1 requests;
- `docs/query-contract.md` — typed-query and cursor semantics;
- `docs/query-load-baseline.md` — measured reference regression;
- `docs/deployment-profiles.md` — App Service and AKS reference deployment;
- `docs/observability.md` — telemetry/OpenTelemetry integration;
- `docs/version-naming.md` — roadmap capability labels and version axes;
- `docs/roadmap.md` — detailed execution roadmap.

## Next release

**CEPIO v0.5 CONNECT — Live Industrial Integration** moves from platform qualification to authoritative industrial context: provenance-backed onboarding, source-neutral connector/extractor foundations, SAP/PI and additional industrial bindings, external identity reconciliation, governed writeback and the K-201 compressor lighthouse proof.
