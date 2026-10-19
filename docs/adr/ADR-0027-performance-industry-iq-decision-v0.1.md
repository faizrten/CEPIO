# ADR-0027: Performance Deviation to Industry IQ Decision v0.1

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1, ADR-0023 Performance Contract Registry v0.1, ADR-0024 Governed Performance Business Logic v0.1, ADR-0025 Enterprise Performance Surfaces and Governed Response v0.1

## Context

CEPIO can now define organization-specific performance semantics, execute governed Business Logic, resolve version-pinned Performance Contracts and expose deterministic deviations through headless surfaces. The next boundary is to turn a material deviation into useful Industry IQ without collapsing three different concerns into one:

1. deterministic performance truth;
2. reasoning/recommendation;
3. governed execution authority.

A red KPI is not a root cause, an `influences` edge is not causal proof, and a matching workflow binding is not authority to start a workflow. CEPIO therefore needs an explicit bridge from Performance evidence to a Decision record while preserving those distinctions.

## Decision

### 1. Preserve the CEPIO source subject through Performance evaluation

`PerformanceObservation.source_subject_id` is carried into `PerformanceNodeEvaluation` and `PerformanceDeviationAssessment`.

This identity is optional at the Performance-evaluation layer because not every enterprise-level metric is tied to one runtime object. It becomes mandatory when Industry IQ attempts to create a Decision about a concrete CEPIO subject.

### 2. Add a Performance response Industry IQ capability

The versioned Industry IQ pack is:

```text
cepio.iq.performance.response@0.1.0
```

It registers the named Decision capability:

```text
performance-deviation-response
```

The pack grants no Action capability and registers no workflow execution authority.

### 3. Introduce a protocol-neutral Performance Industry IQ service

`cepio.performance_industry_iq.PerformanceIndustryIQService` composes:

- the existing `PerformanceService`; and
- the existing `CEPIOApplicationService`.

`reason(...)` is side-effect free. It resolves and pins the Performance Contract revision, enforces tenant scope, evaluates the supplied evidence, selects one actionable deviation and returns an explainable `DecisionProposal`.

`propose_decision(...)` is an explicit second operation. It persists the proposal only through `CEPIOApplicationService.propose_decision(...)`, so actor identity, read authorization, named Decision policy and Decision contract validation remain owned by the existing application/runtime boundary.

Neither method starts a workflow or executes an Action.

### 4. Require direct evidence identity before creating a Decision

A propagated `at_risk` state is useful context but is insufficient by itself to create a Decision against a concrete CEPIO object.

v0.1 requires:

```text
deviation.source_subject_id == requested Decision subject ID
```

If a deviation has no direct `source_subject_id`, Industry IQ fails closed with `SOURCE_SUBJECT_REQUIRED`.

This prevents an abstract enterprise KPI propagation from being attached to an arbitrary asset, person, team or other entity.

### 5. Preserve exact customer isolation

For organization-scoped Performance Contracts, the trusted `ExecutionContext.tenant_id` must exactly match the effective contract `organization_id` before evaluation/reasoning proceeds.

Industry-reference contracts remain organization-neutral.

There is no cross-customer fallback, name matching or administrator inference.

### 6. Keep structural risk and influence semantics distinct

Industry IQ may summarize `risk_sources` as upstream structural investigation priorities.

`influence_sources` are rendered explicitly as contextual evidence and **not causal proof**. v0.1 does not infer root cause, quantitative causal effect or intervention impact from an influence edge.

The Decision output carries:

```text
causal_claim_made = false
```

### 7. Workflow candidates remain recommendations

Matching `PerformanceResponseBinding` entries are preserved on the reasoning assessment. The recommendation may tell a user or agent to consider those workflows, but the output remains:

```text
authority = recommend_only
policy_required = true
```

and the persisted result explicitly records:

```text
workflow_started = false
action_executed = false
```

Kinetic Runtime and Workflow Policy remain the only execution boundary.

### 8. Do not copy arbitrary operating properties into Decision records

Callers may supply CEPIO context object IDs. The service reads each object through the authorized application boundary and records only stable object references in the reasoning assessment.

v0.1 does not copy arbitrary authorized object properties into the Decision text. This avoids turning the Decision repository into a secondary disclosure path with different read semantics.

## Resulting chain

```text
Performance evidence
  -> governed Business Logic
  -> version-pinned Performance Contract
  -> deterministic Performance evaluation
  -> directly evidence-backed deviation
  -> Performance Industry IQ reasoning
  -> governed Decision proposal
  -> actor/policy-checked Decision persistence
  -> Workflow Policy (future explicit hand-off)
  -> authorized workflow/action
  -> outcome evidence
```

## Consequences

CEPIO can now move beyond scorecard detection into a governed management loop without letting Performance semantics acquire execution authority.

A Decision has a concrete CEPIO subject and preserves the contract/version, performance evidence, structural risk sources, influence context and matching workflow candidates that motivated the recommendation.

Domain-specific Industry IQ can later enrich the reasoning step while continuing to consume the same deterministic Performance and Decision boundaries.

## Non-goals

v0.1 does not:

- automatically persist a Decision merely because a KPI is off track;
- automatically start a workflow;
- execute an external Action;
- infer root cause with an LLM;
- treat correlation/influence as causation;
- calculate quantitative causal impact;
- choose a `recommended_action` from a workflow binding;
- rank personnel from KPI/OKR performance;
- create a Decision for a propagated-only deviation with no concrete source subject;
- expose a new stable REST/MCP contract.

## Next evolution

The next controlled increment is domain-aware reasoning enrichment. Reliability, drilling, refinery, subsurface and other Industry IQ packs should be able to contribute governed evidence and domain-specific hypotheses to the same Performance reasoning contract without changing Performance truth or Kinetic execution authority.

A later surface can then expose the reasoning/Decision bridge through REST/MCP after qualification, using the same tenant and policy rules rather than reimplementing them in protocol adapters.
