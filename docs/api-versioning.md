# CEPIO Public API Versioning Policy

CEPIO's supported public REST contract is exposed under `/api/v1` through `cepio.public_api:app`.

Unversioned routes remain temporarily for backwards compatibility, but they are not part of the public OpenAPI contract and can be removed after an announced migration period.

## Compatibility rules

The following changes are backwards-compatible within API v1:

- adding a new optional request field;
- adding a new optional response field;
- adding a new endpoint;
- adding a new enum value only where consumers are explicitly documented to tolerate unknown values;
- adding new error detail fields without changing the stable error code.

The following changes are breaking and require an explicit API-version decision and migration plan:

- removing or renaming an endpoint;
- changing an HTTP method for an existing operation;
- removing or renaming a request or response field;
- changing a field type or semantic meaning;
- making an optional request field required;
- changing an operation ID used by generated SDKs;
- changing authentication or authorization semantics in a way that invalidates an existing supported client flow;
- changing documented status-code or stable error-code semantics.

## Contract artifact

`openapi/cepio-v1.yaml` is the accepted route-level API v1 baseline. CI compares the running public FastAPI OpenAPI document to that baseline and fails when a route, method, or operation ID is removed, added without review, or changed.

The baseline must only be updated as part of an intentional API-contract review.

The existing quality-compatibility lane additionally compares complete generated
application and read-only Management documents against the immutable PR base
(previous commit on push). `scripts/check_openapi_compatibility.py` exports both
revisions in isolated processes using in-memory test configuration, without
starting a service, lifespan, model or cloud connection. Evidence includes full
base/head JSON schemas, semantic findings, comparator diagnostics and a result.
Management is a separate contract; experimental and legacy routes are excluded.

The checksum-pinned upstream oasdiff 1.34.0 comparator blocks ERR and WARN changes
to declared parameters, request/response schemas, requiredness, enums, bounds,
references and status/media contracts. Additional strict checks prevent removal
or alteration of authentication requirements/schemes and stable operation IDs.
Positive and negative controls run on every comparison. Missing baseline source,
invalid output, unavailable tools or comparator failures block CI; updating an
accepted route YAML cannot hide a change to the generated base contract. There
is no automatic migration waiver or paid/uploaded comparison service.

Reviewed complete snapshots are stored in `openapi/generated-application-v1.json`
and `openapi/generated-management-v1.json`. The generated head must exactly match
its snapshot; this catches changes from dependency resolution as well as source.
Regenerate deliberately with `python scripts/check_openapi_compatibility.py
--record --surfaces application management`, review the complete diff, and retain
the immutable base comparison. That comparison reads the base commit's snapshot,
so updating a head snapshot cannot conceal an incompatible change. The initial
PR bootstraps from base source because older main has no full snapshot; reports
label this explicitly rather than asserting historical dependency reproducibility.

This checks declared HTTP contracts, not business meaning or actual runtime
authorization. Untyped responses and undocumented error statuses remain explicit
contract coverage gaps; signed identity, tenant/property, replay and consumer
tests remain required. MCP tools/protocols are not OpenAPI HTTP operations.
Production qualification and release/maturity claims remain unchanged.

## Resource families

The initial v1 surface includes:

- objects;
- relationships and neighbour traversal;
- typed object queries;
- operational events;
- graph analytics;
- functions;
- actions;
- decisions;
- audit;
- service health.

Future `state`, `provenance`, and `schema` resources should be added only when their runtime contracts are stable enough to support independent clients.

## Security inheritance

API v1 aliases the same secured CEPIO endpoint functions used by the compatibility routes. Authentication, actor derivation, object/property read filtering, function authorization, graph-role restrictions, action policy and audit therefore remain single-sourced rather than being reimplemented for v1.

## SDK and MCP alignment

REST, Python SDK, TypeScript SDK, and MCP should expose the same CEPIO semantic operations rather than inventing separate domain semantics. SDKs are convenience layers over the stable CEPIO contract; MCP is an agent-facing projection of the same underlying capabilities.
