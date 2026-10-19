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

## Runtime evaluation

`cepio.performance_runtime.PerformanceRuntime` evaluates observations deterministically.

An observation must carry evidence references and a timezone-aware timestamp. The evaluator uses the latest observation at or before evaluation time, applies freshness/validity checks, evaluates targets and thresholds, and reports one of:

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

## From performance deviation to execution

Performance does not execute side effects directly.

A response binding maps a performance state to a workflow definition:

```yaml
response_bindings:
  - id: availability-investigation
    node_id: availability
    statuses: [off_track, critical]
    workflow_definition_id: investigate-availability-loss
```

The evaluator returns a workflow candidate with:

```text
authority = recommend_only
policy_required = true
```

The hand-off is therefore:

```text
Performance Contract / resolved specialization
      -> Performance Runtime
      -> recommend-only Workflow Candidate
      -> Kinetic Runtime
      -> Workflow Policy Boundary
      -> Skill / Workflow / governed Action
      -> Outcome evidence
```

CEPIO's existing policy, approval and external-action controls remain the only authority for side effects.

## Example

See [`examples/performance_contract_refinery.yaml`](../../examples/performance_contract_refinery.yaml).

The example contains an enterprise objective, COO KPI, individual key result, maintenance-cost guardrail, explicit contribution graph and a governed availability-investigation response binding.

## What v0.1 intentionally does not do

- no formula execution inside the Performance Runtime;
- no quantitative causal-impact calculation from graph edges;
- no automatic workflow start;
- no REST/MCP persistence surface yet;
- no implicit KPI cascade;
- no overlay deletion/tombstone semantics;
- no cross-customer contract inheritance;
- no performance-based personnel ranking or opaque scoring.

These boundaries keep organization meaning explicit and preserve CEPIO's recommend-before-execute architecture.

## Next evolution

With deterministic contract specialization in place, the next capability sequence is:

```text
Durable Performance Contract Registry
        -> Business Logic / formula execution contract
        -> REST + MCP performance surfaces
        -> governed performance-to-workflow activation
```

The durable registry should add version selection and lifecycle without weakening the current active-ID and customer-isolation rules. Business Logic execution should remain separate from ontology semantics so customer formulas can be governed, versioned and provenance-backed without becoming universal CEPIO definitions.

See [ADR-0021](../adr/ADR-0021-enterprise-performance-graph-v0.1.md) for the base performance architecture and [ADR-0022](../adr/ADR-0022-performance-contract-specialization-v0.1.md) for specialization.
