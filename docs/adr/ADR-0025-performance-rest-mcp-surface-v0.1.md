# ADR-0025: Enterprise Performance REST + MCP Surface v0.1

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1, ADR-0023 Performance Contract Registry v0.1, ADR-0024 Governed Performance Business Logic v0.1

## Context

CEPIO now has a semantic Performance Contract, deterministic specialization, immutable
versioned registry, and governed Business Logic execution. Industry IQ, agents and
external applications still need a supported headless surface to resolve effective
performance meaning and evaluate current evidence.

The public boundary must preserve customer isolation and CEPIO's existing authority
model. In particular:

- an Entra tenant ID is an identity-provider tenant, not a CEPIO organization semantic;
- supplying an `organization_id` in a request must never grant access by itself;
- formula execution must retain existing `PolicyEngine.can_call_function` controls;
- Performance Runtime workflow candidates are recommendations, not workflow/action
  authority; and
- registry or formula mutation belongs to the management/control plane, not the public
  read/evaluate API.

## Decision

CEPIO adds a shared `PerformanceService` consumed by REST and MCP.

### 1. Explicit tenant -> CEPIO organization mapping

The host configures an explicit mapping with `CEPIO_TENANT_ORGANIZATION_MAP`:

```json
{
  "entra-tenant-a": ["refinery-co", "petchem-co"]
}
```

A tenant-bound performance request is allowed only when the authenticated actor's
`tenant_id` maps to the requested CEPIO `organization_id`.

CEPIO does **not** infer that `tenant_id == organization_id`. An absent tenant, absent
mapping or different organization fails closed. Even `cepio_admin` does not silently
bypass this customer boundary; cross-customer administration must be expressed in the
host mapping.

### 2. Existing semantic/read policy remains authoritative

After organization-scope authorization, the actor must be permitted to read the CEPIO
`KPI` type through the existing policy engine. This reuses CEPIO's role/read contract
rather than introducing a parallel performance-role table.

For governed Business Logic, the service also checks
`PolicyEngine.can_call_function(actor.roles, function_name)` before invoking the trusted
function runtime.

### 3. Public REST v1 is read/evaluate only

Two versioned operations are added:

```text
GET  /api/v1/performance/organizations/{organization_id}/contracts/{contract_id}
POST /api/v1/performance/organizations/{organization_id}/contracts/{contract_id}/evaluate
```

Both support an optional explicit contract `version`; omission selects the active
immutable revision through the Performance Contract Registry.

`GET` returns the fully resolved contract plus the exact source revision chain.

`POST .../evaluate` accepts evidence-backed direct observations and optional governed
Business Logic invocations. It returns:

- contract ID/version;
- immutable source revision references;
- Business Logic execution lineage; and
- the existing deterministic `PerformanceEvaluation` including any recommend-only
  workflow candidates.

The endpoint does not create, update, activate or retire contracts or Business Logic
definitions.

### 4. Observation-source ambiguity fails closed

A node cannot receive both a direct observation and a formula-materialized observation in
the same evaluation request. This avoids hidden precedence rules between reported and
derived values.

Multiple historical direct observations remain valid; the existing Performance Runtime
continues to select the latest eligible evidence deterministically.

### 5. Freshness remains node-owned

No API-level global staleness override is introduced. Existing
`PerformanceNode.max_observation_age_seconds` remains the canonical freshness policy, and
governed Business Logic retains its own input-age contract. The public surface cannot
weaken either rule.

### 6. MCP uses the same service boundary

When a host supplies a configured `PerformanceService`, `MCPFacade` advertises:

- `cepio_performance_resolve`
- `cepio_performance_evaluate`

The MCP facade passes the host actor ID, roles and tenant ID into the same service used by
REST. It does not contain a second customer-scope or formula-authorization implementation.
Hosts that do not configure the performance service retain the existing MCP tool set
unchanged.

### 7. Public API contract change is explicit and protected

The accepted `openapi/cepio-v1.yaml` baseline is updated with the two operations. This is
an intentional public-contract expansion and remains subject to CEPIO compatibility,
governance, architecture, security, quality and CodeQL gates.

## Consequences

### Positive

- Industry IQ can consume Enterprise Performance headlessly over REST or MCP.
- REST and MCP share one authorization/evaluation implementation.
- Customer boundaries are explicit rather than inferred from identity-provider IDs.
- Contract revision provenance and formula execution lineage survive the public boundary.
- Existing KPI read and function-call policies remain authoritative.
- Performance evaluation still cannot execute workflows or external actions.

### Trade-offs

- Deployment must configure tenant-to-organization mappings before tenant-bound
  performance access works.
- The v0.1 public API intentionally has no contract/formula mutation operations.
- Business Logic definitions are still host-registered/in-memory; durable publication is
  a management-plane concern deferred beyond this surface.

## Non-goals

This ADR does not introduce:

- contract or Business Logic publication APIs;
- automatic tenant/organization inference;
- cross-customer access by default;
- workflow start or action execution from Performance Runtime;
- arbitrary formula expressions;
- customer-data training or pooling.

## Validation

Validation covers:

- tenant-to-organization mapping configuration and fail-closed parsing;
- KPI read authorization and formula function authorization;
- explicit and active contract-version resolution;
- REST authentication, customer isolation and structured errors;
- direct-observation and governed-formula evaluation;
- REST OpenAPI route identity;
- MCP optional tool advertisement and shared-service execution;
- MCP tenant isolation and function authorization; and
- preservation of recommend-only workflow semantics.
