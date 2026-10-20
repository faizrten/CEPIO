# ADR-0024: Governed Performance Business Logic v0.1

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1, ADR-0023 Performance Contract Registry v0.1

## Context

A Performance Contract deliberately standardizes the grammar of performance without
making one customer's KPI formula a CEPIO-global truth. Formula-bearing performance
nodes already carry `formula_ref`, including immutable references such as:

```text
logic://refinery-co/availability/v7
```

The Performance Runtime evaluates evidence-backed observations, but it intentionally does
not execute formulas. CEPIO already has a trusted typed-function runtime for deterministic
industrial calculations. Introducing a second arbitrary expression language, `eval`, or
SQL-as-formula would duplicate that execution surface and create an unsafe path around
existing validation and governance.

## Decision

CEPIO adds a governed Business Logic boundary that resolves an exact `formula_ref` to an
immutable `BusinessLogicDefinition`, dispatches only to a function already registered in
the trusted CEPIO function runtime, and materializes the result as an ordinary
`PerformanceObservation`.

### 1. `formula_ref` remains the immutable semantic pointer

The Business Logic Registry keys definitions by the exact `formula_ref` string already
stored on a Performance node. Registering a second definition under the same reference
fails closed.

A definition declares:

- exact `formula_ref`;
- trusted CEPIO `function_name`;
- exact input names;
- optional organization scope;
- optional structured output path;
- optional output unit; and
- optional maximum input age.

This contract does not introduce a parallel KPI identity or formula ontology.

### 2. No arbitrary expression execution

The Business Logic Runtime never evaluates customer-provided Python, JavaScript, SQL,
expression strings, or model-generated code. The referenced function must already be
registered in the trusted CEPIO runtime. Existing function input/output typing therefore
remains authoritative.

This lets CEPIO reuse deterministic functions already present in the runtime while keeping
Business Logic governance separate from implementation code.

### 3. Evidence is mandatory and freshness is conservative

Every formula input carries:

- input name and value;
- timezone-aware observation time; and
- one or more evidence references.

The supplied input set must exactly match the definition contract. Future, naive, stale,
missing, duplicate, or unexpected inputs fail closed.

A derived performance observation is timestamped at the **oldest required input time**,
not execution time or newest input time. This prevents a newly calculated KPI from
appearing fresher than its oldest required source evidence.

Source evidence references are unioned deterministically into the resulting
`PerformanceObservation`.

### 4. Formula lineage is retained separately from source values

A `BusinessLogicExecution` records:

- exact formula reference;
- deterministic definition hash;
- trusted function name;
- organization scope;
- evaluation and effective observation times;
- output value/unit;
- source evidence references; and
- per-input timestamps/evidence references.

Input values are intentionally excluded from the lineage record. This gives future audit,
API, MCP and workflow layers a reproducible execution anchor without creating another
store of customer operational values.

### 5. Customer scope and units fail closed

An organization-bound Business Logic definition may execute only against a Performance
Contract with the same effective organization ID. Organization-neutral definitions can be
reused across customers.

If both the Business Logic definition and Performance node declare units, they must match.

### 6. Existing Performance Runtime remains authoritative

Formula execution does not directly evaluate KPI health, propagate risk, or start a
workflow. It creates a normal `PerformanceObservation` and returns execution lineage.
The existing Performance Runtime then applies targets, thresholds, graph propagation and
recommend-only workflow bindings.

```text
Performance node + formula_ref
          |
Business Logic definition
          |
Trusted CEPIO function
          |
Evidence-backed derived observation
          |
Existing Performance Runtime
          |
Status / deviation / recommend-only workflow candidate
```

## Consequences

### Positive

- organization-specific KPI formulas become executable without polluting CEPIO Core;
- existing trusted industrial calculations are reused instead of duplicated;
- formula execution is deterministic, evidence-backed and customer-scoped;
- historical formula meaning is anchored by exact formula refs and definition hashes;
- derived observations plug directly into the existing performance evaluator;
- execution lineage avoids duplicating raw customer input values.

### Trade-offs

- v0.1 requires an exact input set rather than optional/variadic formula inputs;
- changing formula meaning requires a new immutable `formula_ref`;
- only trusted host-registered functions can execute;
- distributed/durable Business Logic definition storage is deferred.

## Non-goals

This ADR does not introduce:

- arbitrary expression evaluation;
- SQL-as-formula execution;
- model-generated executable code;
- quantitative causal inference;
- automatic workflow/action execution;
- REST/MCP endpoints;
- customer-data training or cross-customer pooling.

## Validation

Tests cover:

- execution through the real `CEPIORuntime` typed-function boundary;
- structured and direct numeric outputs;
- integration with the existing Performance Runtime;
- immutable formula registration;
- organization and unit boundaries;
- exact input contracts;
- timestamp/freshness controls;
- trusted-function absence and execution failures;
- output path, numeric and finite-value validation;
- formula execution lineage and raw-input-value exclusion; and
- deterministic batch materialization.
