# Enterprise Performance Graph

## Purpose

The Enterprise Performance Graph models **how an industrial organization defines success, assigns accountability, observes health and expresses desired change**.

CEPIO treats two management constructs as complementary rather than interchangeable:

- **KPIs** describe persistent operating health or boundaries.
- **OKRs** describe desired, usually time-bound change.

A KPI can exist without an OKR. A key result can depend on one or more KPIs. Both can be connected to operational evidence and organizational accountability.

## Two dimensions

### Performance dimension

```text
Strategy
  -> Objective
  -> Outcome / Key Result
  -> KPI / Guardrail
  -> Metric
  -> Operational evidence
```

### Organizational dimension

```text
Enterprise
  -> Business Unit
  -> Function
  -> Team
  -> Role / Persona
  -> Individual
```

A Performance Contract links the two through explicit accountability. CEPIO does **not** mechanically copy a CEO KPI onto every downstream person.

## Performance Contract v0.1

`cepio.performance_contract.PerformanceContract` contains:

- subjects: enterprise, business unit, function, team, role, persona, individual;
- nodes: objective, outcome, key result, KPI, metric, guardrail;
- targets and thresholds;
- accountability assignments;
- contribution/dependency/influence/constraint relationships;
- response bindings that can recommend governed workflows;
- validity, formula and reference-KPI metadata.

### Organization-specific KPIs

CEPIO standardizes the **contract grammar**, not the customer's KPI formula.

For example, an organization can define:

```yaml
id: availability
kind: kpi
name: Operational availability
definition: Organization-specific operational availability definition
formula_ref: logic://refinery-co/availability/v7
reference_node_id: cepio.reference.refinery.operational-availability
target:
  operator: gte
  value: 0.96
```

`reference_node_id` connects the enterprise definition to an industry/reference concept. `formula_ref` points to the authoritative Business Logic definition. This avoids treating one customer's exclusions, denominator or aggregation rule as a universal CEPIO definition.

## Accountability versus contribution

Accountability relationships answer **who is responsible or involved**:

- `owns`
- `accountable_for`
- `contributes_to`
- `influences`

Performance contribution relationships answer **how performance nodes relate**:

- `contributes_to`
- `depends_on`
- `influences`
- `constrains`

Example:

```text
Individual KR: reduce repeat compressor failures
             |
             | contributes_to
             v
KPI: operational availability
             |
             | contributes_to
             v
Objective: improve refinery profitability
```

The individual owns the KR. The COO can be accountable for availability. Neither relationship means the individual owns refinery profitability.

## Contract specialization

`cepio.performance_resolution.PerformanceContractResolver` composes explicit performance-contract layers:

```text
Industry Reference
       |
       v
Organization
       |
       v
Role / Persona
       |
       v
Individual
```

The chain is explicit through `extends_contract_id`; CEPIO never infers inheritance from similar names, KPI labels, persona similarity or organization structure.

### Complete contracts versus sparse overlays

A `PerformanceContract` is complete, strictly validated and directly evaluable. A `PerformanceContractOverlay` is intentionally sparse and exists only as specialization input.

This separation allows a role/persona or individual layer to reference inherited subjects and performance nodes without copying the entire enterprise graph. The resolver emits a new fully validated `PerformanceContract`; unresolved overlays are never treated as authoritative enterprise truth.

### Specialization is not KPI cascade

Inheritance provides context, not automatic personal accountability.

An enterprise `Operational Availability` KPI can remain scoped to Operations while a Reliability Engineer persona owns a `Reduce Repeat Failures` key result that explicitly `contributes_to` availability. An individual can contribute to that KR without becoming owner of the enterprise KPI.

### Override rules

Child layers can add entries or explicitly replace an inherited entry with the same stable identity. Subject kind and performance-node kind cannot mutate across an override.

v0.1 deliberately has no implicit field patching, deletion, suppression or tombstone semantics. A child override is a whole-entry replacement so inherited meaning cannot disappear through an ambiguous partial merge.

### Customer boundary and provenance

Industry-reference contracts are organization-neutral. Once an organization ID appears in a specialization chain, descendants cannot cross to another organization ID.

Resolution records both the ordered source-contract chain and element-level lineage for effective subjects, nodes, accountabilities, contributions and response bindings. When an organization or role overrides a reference definition, Industry IQ can therefore explain exactly which contract/version supplied the effective meaning.

Effective validity is the intersection of all layers. A chain with no overlapping effective window fails closed.

See [ADR-0022](../adr/ADR-0022-performance-contract-specialization-v0.1.md) for the specialization contract.

## Durable Performance Contract Registry

`cepio.performance_registry.PerformanceContractRegistry` makes Performance Contracts operational rather than file-local definitions.

It provides:

- immutable versioned contract revisions;
- draft / active / retired lifecycle;
- one active revision per contract identity;
- version-pinned parent selection for specialized contracts;
- durable source-revision hashes;
- in-memory and SQLite reference stores;
- exact organization-scope validation.

The effective contract is resolved from pinned revisions. Changing which revision is active later does not rewrite historical contract lineage.

See [ADR-0023](../adr/ADR-0023-performance-contract-registry-v0.1.md).

## Governed Business Logic

Organization-specific KPI formulas remain outside ontology semantics.

`cepio.performance_business_logic` provides the governed execution boundary for formula definitions referenced by `formula_ref`. The purpose is to let a customer version, validate and execute its own business logic without turning that logic into a universal CEPIO semantic definition.

Performance therefore separates:

```text
semantic identity / target / accountability
                from
customer formula implementation
```

See [ADR-0024](../adr/ADR-0024-performance-business-logic-v0.1.md).

## Runtime evaluation

`cepio.performance_runtime.PerformanceRuntime` evaluates observations deterministically.

An observation must carry evidence references and a timezone-aware timestamp. It may also carry `source_subject_id`, linking the measured result to a concrete CEPIO object. The evaluator preserves that subject identity through node evaluation and deviation assessment so a later governed Decision can be anchored to real enterprise state.

The evaluator uses the latest observation at or before evaluation time, applies freshness/validity checks, evaluates targets and thresholds, and reports one of:

- `unknown`
- `not_evaluated`
- `on_track`
- `watch`
- `at_risk`
- `off_track`
- `critical`

Missing or stale evidence fails closed to `unknown`.

### Risk propagation is conservative

Structural edges (`contributes_to`, `depends_on`, `constrains`) can mark an unobserved downstream node `at_risk` when an upstream node is materially off track.

An `influences` edge is different: it is surfaced as context but does not automatically mark the target `at_risk`. CEPIO therefore does not convert association into a causal claim.

If a downstream KPI has direct evidence, its directly evaluated status remains authoritative. Upstream risk sources are still exposed alongside it.

## Guardrails

Guardrails are first-class nodes. This allows balanced performance definitions such as:

```text
Reduce maintenance cost
        |
        +-- guardrail: asset reliability must not deteriorate
        +-- guardrail: critical backlog must remain below threshold
        +-- guardrail: safety/integrity boundary must remain satisfied
```

This provides the foundation for detecting local KPI optimization that harms the wider system.

## Headless Performance surfaces

`cepio.performance_service.PerformanceService` is the protocol-neutral application boundary over the registry and deterministic runtime.

It returns:

- resolved contract identity/version;
- organization scope;
- source-revision hashes;
- full deterministic evaluation;
- actionable deviations;
- matching response workflow candidates.

The first REST surface is under `/experimental/performance/v0.1` and intentionally excluded from the stable OpenAPI contract. Performance MCP capability is also additive through a separate `PerformanceMCPFacade`, leaving the stable `MCPFacade` unchanged.

Both surfaces enforce exact tenant isolation for organization-scoped contracts. Industry-reference contracts remain tenant-neutral reference intelligence.

See [ADR-0025](../adr/ADR-0025-performance-surfaces-response-v0.1.md).

## From performance deviation to Industry IQ Decision

A response binding still maps a performance state to a **workflow candidate**, not execution authority:

```yaml
response_bindings:
  - id: availability-investigation
    node_id: availability
    statuses: [off_track, critical]
    workflow_definition_id: investigate-availability-loss
```

The candidate remains:

```text
authority = recommend_only
policy_required = true
```

CEPIO now adds a separate Industry IQ reasoning bridge in `cepio.performance_industry_iq`.

The versioned capability pack is:

```text
cepio.iq.performance.response@0.1.0
```

and it registers the named Decision capability:

```text
performance-deviation-response
```

`PerformanceIndustryIQService.reason(...)` is side-effect free. It:

1. resolves the exact Performance Contract revision;
2. checks the trusted tenant against the contract organization;
3. evaluates evidence using the deterministic Performance Runtime;
4. selects an actionable deviation;
5. requires a concrete `source_subject_id` matching the requested CEPIO Decision subject;
6. summarizes structural risk sources separately from non-causal influence context;
7. preserves matching workflow candidates as recommend-only options; and
8. returns an explainable `DecisionProposal`.

`propose_decision(...)` is an explicit second step. It persists the Decision only through `CEPIOApplicationService.propose_decision(...)`, preserving actor identity, object-read policy, named Decision authorization and runtime Decision validation.

The resulting chain is:

```text
Performance evidence
      -> governed Business Logic
      -> version-pinned Performance Contract
      -> deterministic Performance evaluation
      -> directly evidence-backed deviation
      -> Industry IQ reasoning
      -> governed Decision proposal
      -> actor/policy-checked Decision record
      -> Workflow Policy
      -> authorized workflow/action
      -> outcome evidence
```

### Why propagated risk alone cannot create a Decision

An unobserved downstream KPI can become `at_risk` through a structural contribution chain. That is useful management context, but it does not identify a concrete runtime subject.

v0.1 therefore refuses to create a Decision from a propagated-only deviation unless direct evidence provides `source_subject_id`. This prevents an abstract enterprise KPI from being attached to an arbitrary asset, person or other CEPIO object.

### Why influence is not root cause

Influence nodes are surfaced in Decision observations as:

```text
Influence context (not causal proof)
```

The Industry IQ assessment explicitly records `causal_claim_made = false`. Domain-specific reasoning may later add hypotheses and additional governed evidence, but it must not rewrite an influence edge into causal truth.

### Context does not become a new disclosure channel

Callers may supply authorized CEPIO context object IDs. The reasoning service validates them through the application-service read boundary and stores stable references in its assessment.

It does not copy arbitrary object properties into Decision text, avoiding a secondary persistence surface with different disclosure semantics.

See [ADR-0026](../adr/ADR-0026-performance-industry-iq-decision-v0.1.md).

## Example

See [`examples/performance_contract_refinery.yaml`](../../examples/performance_contract_refinery.yaml).

The example contains an enterprise objective, COO KPI, individual key result, maintenance-cost guardrail, explicit contribution graph and a governed availability-investigation response binding.

## Current safety boundaries

Enterprise Performance intentionally does **not**:

- infer quantitative causal impact from contribution/influence edges;
- automatically start workflows;
- execute external Actions;
- automatically persist Decisions merely because a KPI is red;
- create a Decision for propagated-only risk with no concrete source subject;
- implicitly cascade enterprise KPIs into personal accountability;
- permit cross-customer contract inheritance or reasoning;
- rank personnel from KPI/OKR performance;
- make experimental Performance REST routes part of the stable `/api/v1` contract.

These boundaries preserve CEPIO's recommend-before-execute architecture.

## Next evolution

The next controlled evolution is **domain-aware Industry IQ enrichment**:

```text
Deterministic Performance deviation
        -> generic Performance Industry IQ reasoning
        -> domain pack evidence / hypotheses
        -> governed Decision
        -> Workflow Policy
```

Reliability, drilling, refinery, subsurface and other Industry IQ packs should contribute domain-specific evidence and hypotheses without changing the underlying Performance truth or acquiring Kinetic execution authority.

After that reasoning contract is qualified, the same capability can be exposed through REST/MCP without moving semantic or policy ownership into protocol adapters.

See [ADR-0021](../adr/ADR-0021-enterprise-performance-graph-v0.1.md), [ADR-0022](../adr/ADR-0022-performance-contract-specialization-v0.1.md), [ADR-0023](../adr/ADR-0023-performance-contract-registry-v0.1.md), [ADR-0024](../adr/ADR-0024-performance-business-logic-v0.1.md), [ADR-0025](../adr/ADR-0025-performance-surfaces-response-v0.1.md) and [ADR-0026](../adr/ADR-0026-performance-industry-iq-decision-v0.1.md).
