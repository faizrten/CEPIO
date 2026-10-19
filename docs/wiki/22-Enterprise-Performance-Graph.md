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
Performance Contract
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

- no automatic contract inheritance/overlay merge;
- no formula execution inside the Performance Runtime;
- no quantitative causal-impact calculation from graph edges;
- no automatic workflow start;
- no REST/MCP persistence surface yet;
- no performance-based personnel ranking or opaque scoring.

These boundaries keep organization meaning explicit and preserve CEPIO's recommend-before-execute architecture.

## Next evolution

The natural next layer is contract specialization:

```text
CEPIO Industry Reference Performance Contract
                 |
                 v
Organization Performance Contract
                 |
                 v
Role / Persona Performance Contract
                 |
                 v
Individual Assignment / OKR Overlay
```

Each layer should preserve provenance, effective dates and explicit overrides. Customer-specific logic stays tenant-scoped while reusable industry patterns remain in CEPIO Industry IQ.

See [ADR-0021](../adr/ADR-0021-enterprise-performance-graph-v0.1.md) for the architectural decision.
