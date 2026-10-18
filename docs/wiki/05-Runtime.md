# CEPIO Runtime

## Role of the runtime

The ontology defines industrial meaning. The runtime makes that meaning executable.

The CEPIO runtime is responsible for:

- object lifecycle;
- relationship validation;
- temporal history;
- event storage and state projection;
- query execution;
- function invocation;
- decision recording;
- policy evaluation;
- governed action execution;
- audit;
- external adapter orchestration.

## Repository contracts

The runtime is designed around repository abstractions rather than a single database.

Key domain-facing repositories include object, event, decision and audit persistence.

Reference implementations currently support:

- in-memory execution for tests and examples;
- SQLite for durable local/reference execution.

## Object versioning

Objects carry integer versions. Mutations may provide `expected_version` to enforce optimistic concurrency.

```text
read object version 12
        |
update expected_version=12
        |
        +-- current version 12 -> commit version 13
        |
        +-- current version 13 -> concurrency conflict
```

This prevents silent overwrite of newer state.

## Event-driven state projection

Events are immutable. Derived state can be rebuilt deterministically.

Ordering uses:

```text
(occurred_at, event_id)
```

This provides reproducibility when multiple events share timestamps.

## Type registry

The runtime resolves ontology classes and relationships through a registry built from RDF/OWL modules.

Responsibilities include:

- canonical identity resolution;
- inheritance;
- relationship domain/range constraints;
- alias handling;
- module metadata.

## Function runtime

The function runtime invokes typed calculations and reasoning operations over CEPIO objects and relationships.

Functions should be deterministic where practical and should expose explicit typed inputs/outputs.

## Action runtime

The action runtime governs side-effecting operations.

Execution order follows the principle:

```text
resolve target
 -> resolve action definition
 -> policy evaluation
 -> idempotency replay check
 -> preconditions
 -> effect handler
 -> immutable audit
 -> optional external adapter
```

Policy is evaluated before replaying prior idempotent results so idempotency cannot become an authorization bypass.

## Graph intelligence

CEPIO includes backend-neutral graph analytics.

Reference execution uses NetworkX. Optional RAPIDS `nx-cugraph` acceleration can be enabled where useful.

Supported patterns include:

- PageRank;
- degree centrality;
- betweenness centrality;
- eigenvector centrality;
- Louvain communities;
- dependency traversal;
- blast-radius analysis.

NVIDIA acceleration is optional. CEPIO owns the graph semantics.

## Runtime maturity

### Implemented/reference

- in-memory and SQLite persistence;
- typed queries;
- bitemporal history;
- event projection;
- functions/actions;
- policy hooks;
- MCP facade;
- Fabric IQ binding generation;
- graph analytics.

### Still evolving toward production

- enterprise-scale persistence;
- high availability;
- multi-tenancy;
- complete production adapters;
- production SLOs;
- full observability;
- large-scale load/performance program.

## Workflow policy v0.5.1

[Workflow policy integration](../workflow-policy-v0.5.1.md) binds exact policy versions to durable workflow instances, derives trusted canonical context, pauses governed actions for human approval, and persists policy evidence through Action, external execution and Outcome.


## Skill dispatch admission

The host filters static BOUND candidates through actor-aware READY preflight before trigger matching. Only a unique match dispatches; conflicts fail closed. See [the contract](../skill-runtime-preflight.md#v023-ready-only-dispatch). Preflight stays outside Operator tools; evidence sufficiency is evaluated during invocation.
