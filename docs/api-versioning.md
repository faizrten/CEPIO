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

The baseline must only be updated as part of an intentional API-contract review. As API v1 hardening continues, schema-level compatibility checks will be added for request/response models and common error responses.

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
