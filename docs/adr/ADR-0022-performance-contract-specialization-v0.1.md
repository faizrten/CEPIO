# ADR-0022: Performance Contract Specialization v0.1

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1

## Context

ADR-0021 established Enterprise Performance Graph semantics for objectives, outcomes,
key results, KPIs, metrics, guardrails, accountability, contribution relationships and
governed response bindings. The contract also introduced explicit layers:
`industry_reference`, `organization`, `role`, and `individual`.

A useful Industry IQ runtime must specialize those semantics without copying the entire
enterprise graph into every organization, role, persona or individual contract. It must
also preserve customer boundaries: reusable industry intelligence may be shared, while
customer-specific definitions, formulas, targets and accountabilities remain owned by
the customer context that supplied them.

The existing `PerformanceContract` is intentionally strict. All graph references must
resolve inside the contract, and the result is safe to pass directly to the performance
evaluator. Relaxing that validator for child contracts would allow unresolved partial
contracts to be mistaken for complete enterprise truth.

## Decision

CEPIO introduces a deterministic Performance Contract specialization resolver and a
separate sparse `PerformanceContractOverlay` type.

A complete `PerformanceContract` remains the only directly evaluable performance
contract. An overlay is an inheritance input and MUST be resolved before evaluation.
The resolver produces a new fully validated `PerformanceContract` plus element-level
lineage.

### Explicit inheritance

Inheritance is opt-in through `extends_contract_id`. CEPIO does not infer a parent from
names, subject hierarchy, persona similarity, organization membership or KPI labels.

The intended specialization direction is:

```text
industry_reference -> organization -> role/persona -> individual
```

The `role` layer covers both concrete roles and reusable personas. Layers may be
skipped, but a chain may never move backwards or specialize twice at the same layer in
v0.1.

### Sparse overlays

An overlay may add subjects, performance nodes, accountabilities, contributions and
response bindings while referring to inherited subjects/nodes. This enables a role or
individual layer to add only the semantics that are truly specific to that context.

The resolver validates the final merged graph using the existing strict
`PerformanceContract` validator. Dangling references, invalid subject hierarchies and
structural contribution cycles therefore still fail closed.

### Override semantics

Element identity is stable across the inheritance chain.

- Subjects are keyed by subject ID.
- Performance nodes are keyed by node ID.
- Response bindings are keyed by binding ID.
- Accountabilities are keyed by `(subject, node, relation)`.
- Contributions are keyed by `(source node, target node, relation)`.

A child entry with an inherited identity is an explicit whole-entry override. The child
becomes the effective source for that element. A subject kind or performance-node kind
MUST NOT change across an override; such changes are semantic identity mutations and
fail closed.

v0.1 intentionally provides no implicit field-level patching, deletion, suppression or
tombstone directive. Those operations require an explicit future contract so inherited
semantics cannot disappear accidentally.

### No implicit KPI cascade

Inheritance does not mean that every enterprise KPI becomes an individual KPI. A child
receives the inherited graph as context, then explicitly adds or overrides only the
performance semantics relevant to that layer. Accountability remains explicit.

For example, an enterprise `Operational Availability` KPI can remain an enterprise or
operations KPI while a Reliability Engineer persona owns a `Reduce Repeat Failures`
key result that contributes to availability. An individual may contribute to that key
result without being declared owner of the enterprise KPI.

### Organization boundary

Industry-reference contracts must be organization-neutral. The first organization ID
encountered in a specialization chain establishes the customer boundary. Any descendant
that declares a different organization ID is rejected.

This is a semantic isolation rule. Specialization reuses CEPIO/Industry IQ reference
intelligence; it does not merge customer-specific performance contracts across tenants.

### Effective time

The effective validity of a resolved contract is the intersection of all specialization
layers. If the layers have no overlapping effective window, resolution fails closed.

### Provenance

Resolution returns:

1. the ordered source-contract chain; and
2. element-level lineage identifying the contract ID, version and layer that supplied
   each effective subject, node, accountability, contribution and response binding.

When a child overrides an inherited element, lineage follows the effective child entry.
This allows Industry IQ explanations to answer both "what is the effective performance
contract?" and "where did this definition come from?"

### Execution boundary

Specialization changes semantic composition only. It does not execute formulas, start
workflows, authorize actions or perform external side effects. ADR-0021's existing
Performance Runtime and Kinetic/Workflow Policy boundaries remain authoritative.

## Consequences

### Positive

- Industry reference intelligence becomes reusable without copying customer contracts.
- Organization-specific KPI definitions and targets remain isolated.
- Role/persona and individual performance can be modeled without naive KPI cascading.
- The evaluator consumes one existing strict contract type after resolution.
- Provenance makes specialization explainable and auditable.
- Overlay errors fail before evaluation or workflow recommendation.

### Trade-offs

- An active resolver registry requires unique contract IDs; historical version selection
  is deferred to the future persistence/registry capability.
- Whole-entry overrides are more verbose than field-level patches but are unambiguous.
- Same-layer inheritance is not supported in v0.1.
- Removal/tombstone semantics are deliberately deferred.

## Deferred

The following remain outside v0.1:

- durable contract persistence and version registry;
- field-level patch and explicit tombstone contracts;
- formula/business-logic execution;
- REST/MCP performance contract surfaces;
- automatic workflow start;
- quantitative causal inference or learned contribution weights;
- cross-customer performance-contract inheritance.

## Validation

Focused tests cover:

- full industry -> organization -> role/persona -> individual resolution;
- sparse references to inherited subjects and nodes;
- direct evaluation of the fully resolved contract;
- deterministic override provenance;
- contribution metadata refinement;
- node/subject identity mutation rejection;
- missing parents and inheritance cycles;
- invalid layer order;
- cross-organization inheritance rejection;
- effective-window intersection;
- final strict graph validation after composition; and
- duplicate active contract IDs.
