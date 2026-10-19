# ADR-0025: Enterprise Performance Surfaces and Governed Response v0.1

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1, ADR-0023 Performance Contract Registry v0.1, ADR-0024 Governed Performance Business Logic v0.1

## Context

CEPIO now has a deterministic Enterprise Performance Graph, explicit contract specialization, a durable version-pinned Performance Contract Registry and governed Business Logic execution. The next boundary is to make this capability consumable by headless applications and agents without moving semantic ownership into REST/MCP or weakening CEPIO's recommend-before-execute model.

A performance deviation can be operationally significant, but observing a deviation is not execution authority. The same is true when a Performance Response Binding identifies a relevant workflow definition.

## Decision

### 1. Introduce a protocol-neutral Performance Service

`cepio.performance_service.PerformanceService` is the application boundary over the Performance Contract Registry and Performance Runtime.

It resolves a version-pinned effective contract and evaluates evidence-backed observations. Its output includes:

- the resolved contract identity and version;
- organization scope;
- immutable source-revision hashes;
- the full deterministic Performance Evaluation;
- actionable deviation assessments;
- response workflow candidates.

REST and MCP are adapters over this service. They do not own performance semantics, contract lifecycle or business logic.

### 2. Deviations remain deterministic and explainable

A deviation assessment is emitted only for `watch`, `at_risk`, `off_track` or `critical` performance states. It preserves:

- measured value and timestamp;
- evidence references;
- deterministic evaluation reasons;
- upstream risk sources;
- influence sources; and
- any matching response candidates.

The service does not use an LLM to decide whether a KPI is off track and does not infer causal impact from correlation.

### 3. Performance response remains recommend-only

Every performance response surface preserves:

```text
authority = recommend_only
policy_required = true
```

A matching `PerformanceResponseBinding` may identify a workflow definition, but neither the Performance Service, REST adapter nor MCP adapter starts that workflow.

Any future hand-off to Kinetic execution must still pass the Workflow Policy boundary, authorization, approval and action controls.

### 4. Enforce exact organization isolation at protocol boundaries

Organization-scoped contracts are visible only when the authenticated tenant exactly matches the effective contract `organization_id`.

Industry-reference contracts remain organization-neutral and may be consumed as reusable reference intelligence.

There is no cross-customer fallback, administrator inference or name-based tenant matching in v0.1.

### 5. Pin the authorized revision through evaluation

When a caller requests the active revision, the adapter first resolves and authorizes that exact revision. Evaluation then uses that resolved version rather than looking up the active revision again.

This prevents an activation change between authorization and evaluation from changing the contract being evaluated.

### 6. Qualify REST outside the stable API contract

The first REST surface is mounted under:

```text
/experimental/performance/v0.1
```

It supports resolved-contract reads and performance evaluation only. The routes are excluded from the published OpenAPI schema during qualification, so the supported `/api/v1` contract and generated clients remain unchanged.

No REST mutation surface for contract activation, Business Logic registration or workflow execution is introduced by this ADR.

### 7. MCP capability is opt-in

`MCPFacade` exposes performance tools only when a `PerformanceService` is explicitly configured. Existing MCP consumers retain their current tool set and behavior otherwise.

The performance MCP tools provide resolved-contract read and evaluation capability. They enforce the same tenant boundary and recommend-only response semantics as REST.

## Consequences

CEPIO can now expose the same Enterprise Performance intelligence through multiple protocols while keeping a single semantic/runtime authority.

Industry IQ applications can consume a compact, evidence-backed deviation object instead of reimplementing KPI evaluation, provenance or tenant isolation.

The stable public API remains unchanged until the experimental surface has sufficient qualification evidence.

## Non-goals

v0.1 does not:

- automatically start workflows;
- execute external actions;
- create decisions automatically;
- perform generative root-cause analysis;
- infer quantitative causal effects from contribution edges;
- expose contract or Business Logic mutation through REST/MCP;
- promote the experimental routes into `/api/v1`;
- rank personnel from performance observations.

## Next evolution

The next controlled step is to bind `PerformanceResponseAssessment` into Industry IQ reasoning packs so an agent or skill can explain the deviation, retrieve relevant operating context and propose a governed Decision.

The intended chain is:

```text
Performance evidence
  -> governed Business Logic
  -> resolved Performance Contract
  -> Performance Service
  -> explainable deviation assessment
  -> Industry IQ reasoning
  -> governed Decision
  -> Workflow Policy
  -> authorized workflow/action
  -> outcome evidence
```

The execution boundary remains Kinetic; Enterprise Performance never acquires side-effect authority.
