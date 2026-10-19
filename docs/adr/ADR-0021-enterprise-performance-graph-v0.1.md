# ADR-0021 — Enterprise Performance Graph v0.1

**Status:** Proposed

## Context

Industrial organizations manage performance through a mixture of persistent KPIs and time-bound objectives/key results. The definitions are organization-specific: two organizations can use the same KPI name while applying different formulas, exclusions, aggregation rules, targets, owners and effective periods. Performance also exists at multiple accountability levels: enterprise, business unit, function, role/persona and individual.

A naive KPI hierarchy is insufficient. It encourages mechanical cascading of executive metrics to individuals, conflates operational health with strategic change, and can hide conflicting incentives. CEPIO needs to connect operational evidence to management intent without claiming unsupported causality or bypassing the existing policy/action boundary.

## Decision

Introduce a versioned **Performance Contract** and **Enterprise Performance Graph** as first-class CEPIO performance semantics.

### 1. Keep KPI and OKR semantics distinct

- **KPI / metric / guardrail** nodes represent persistent operating health, boundaries or observations.
- **Objective / outcome / key result** nodes represent desired change and time-bound strategic intent.
- OKRs do not replace KPIs. A key result can depend on or contribute through KPIs.

### 2. Model accountability separately from performance contribution

A Performance Contract contains subjects at enterprise, business-unit, function, team, role, persona and individual levels. Subjects connect to performance nodes using explicit accountability relations:

- `owns`
- `accountable_for`
- `contributes_to`
- `influences`

Performance nodes connect to other performance nodes using explicit contribution relations:

- `contributes_to`
- `depends_on`
- `influences`
- `constrains`

This avoids pretending that an individual directly owns an enterprise outcome such as EBITDA merely because their work contributes to it.

### 3. Standardize contract grammar, not organization meaning

CEPIO preserves generic KPI identities and industry reference semantics. Organization-specific definitions remain in the Performance Contract through `definition`, `formula_ref`, `reference_node_id`, target, threshold and validity metadata.

This allows an organization KPI to specialize an industry reference KPI without making the customer's formula a CEPIO-global truth.

### 4. Evaluate evidence-backed observations deterministically

The Performance Runtime:

1. selects the latest evidence-backed observation at or before the evaluation time;
2. rejects naive timestamps and treats missing/stale evidence as `unknown`;
3. evaluates targets and thresholds deterministically;
4. propagates `at_risk` through structural contribution/dependency/constraint edges when an upstream node is materially off track;
5. exposes `influences` separately without asserting causal risk;
6. retains upstream risk sources even when a directly observed downstream KPI remains healthy.

The runtime does not infer quantitative causal effects from contribution edges. Weights/confidence are descriptive metadata in v0.1, not a license to calculate financial impact.

### 5. Performance response is recommend-only

A `PerformanceResponseBinding` can map a node/status to a workflow definition. Evaluation emits a `PerformanceWorkflowCandidate` with:

- `authority = recommend_only`
- `policy_required = true`

The Performance Runtime never starts a workflow and never performs an external side effect. Existing Kinetic/Workflow Policy boundaries remain authoritative for workflow execution, approval and external actions.

This preserves CEPIO's AI recommend-but-not-execute invariant.

## Conceptual flow

```text
Strategy / Objectives
        |
Outcomes / Key Results
        |
KPIs / Guardrails
        |
Metrics / Operational Evidence
        |
Performance Runtime
        |
Deviation / at-risk signal
        |
recommend-only Workflow Candidate
        |
Kinetic Runtime + Policy Boundary
        |
Skill / Workflow / Action
        |
Outcome Evidence
        +---------------------> Performance Graph
```

The horizontal organizational dimension is:

```text
Enterprise -> Business Unit -> Function -> Team -> Role/Persona -> Individual
```

The two dimensions are linked by accountability, not by automatic KPI copying.

## Guardrails and Goodhart risk

Guardrails are first-class performance nodes. They allow CEPIO to represent counterbalancing conditions such as maintenance cost versus reliability, throughput versus integrity, or speed versus safety. v0.1 exposes the graph and deviations; later assurance can reason about conflicting incentives and optimization behavior across multiple nodes.

## Ontology impact

`ontologies/performance.ttl` adds compatible performance primitives including `PerformanceContract`, `Outcome`, `KeyResult`, `Target`, `Threshold`, `Guardrail`, `Accountability`, `Contribution`, and `PerformanceResponseBinding` while reusing core `Objective`, `KPI`, `Measurement`, `Evidence`, `dependsOn` and `contributesTo`.

This is additive and does not redefine existing KPI semantics, so no breaking ontology migration manifest is required.

## Runtime/API impact

v0.1 ships a Python contract/evaluator surface only:

- `cepio.performance_contract`
- `cepio.performance_runtime`

REST/MCP persistence, contract registry, inherited overlay resolution, quantitative causal models, and automatic workflow-start APIs are intentionally deferred.

## Consequences

### Positive

- separates organizational performance meaning from CEPIO global semantics;
- supports enterprise, role/persona and individual performance in one graph;
- distinguishes persistent KPIs from time-bound OKRs;
- enables traceable contribution chains without naive KPI cascading;
- creates a safe bridge from performance deviation to governed workflow execution;
- supports guardrails and future incentive-conflict reasoning.

### Trade-offs

- organization onboarding must capture KPI definitions and accountabilities explicitly;
- graph edges do not by themselves prove causality;
- v0.1 does not merge parent/child contracts automatically;
- formula evaluation remains an external Business Logic concern referenced by `formula_ref`.

## Follow-on work

1. Performance Contract registry and persistence.
2. Contract specialization/overlay resolution: industry reference -> organization -> role -> individual.
3. Business Logic Contract integration for formula execution and lineage.
4. REST/SDK/MCP read/evaluate surfaces with authorization.
5. Outcome evidence feedback from Kinetic workflow completion.
6. Incentive/guardrail conflict detection and performance assurance.
7. Quantitative causal models only where explicit model/evidence contracts justify them.
