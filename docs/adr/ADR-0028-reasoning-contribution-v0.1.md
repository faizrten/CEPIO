# ADR-0028: ReasoningContribution v0.1 and Reliability Domain Enrichment

- Status: Accepted
- Date: 2026-10-19
- Owners: CEPIO Architecture
- Related: ADR-0008 Core Evidence and Uncertainty, ADR-0021 Enterprise Performance Graph v0.1, ADR-0027 Performance Deviation to Industry IQ Decision v0.1

## Context

ADR-0027 established a safe generic bridge from deterministic Performance deviation to a governed CEPIO Decision. That bridge can explain the deviation, preserve structural-risk and influence context, and recommend governed investigation/workflow candidates, but it is intentionally shallow on domain expertise.

CEPIO already has generic epistemic semantics in Core: Evidence, Claim, Hypothesis, Assumption, Assessment, UncertaintyAssessment, ConfidenceAssessment and InformationGain. Those semantics should be used by Reliability, drilling, refinery, subsurface and other Industry IQ without moving domain reasoning into Core or duplicating a new ontology vocabulary for every domain.

The next architectural requirement is therefore a reusable runtime contract that allows a domain pack to contribute evidence-backed hypotheses and uncertainty to the same Decision path while preserving three boundaries:

1. deterministic Performance truth remains authoritative;
2. domain reasoning remains hypothesis/recommendation, not causal truth;
3. Kinetic Runtime and Workflow Policy remain the only execution authority.

## Decision

### 1. Introduce ReasoningContribution v0.1 as an application/runtime contract

`cepio.reasoning_contribution` defines the reusable contract for domain reasoning output.

A contribution can contain:

- bounded evidence projections;
- hypotheses with explicit supporting and contradicting evidence;
- confidence bands;
- explicit uncertainties;
- information-gain candidates;
- recommend-only intervention options;
- explanatory messages.

The contract is deliberately not a new ontology module. It operationalizes existing Core epistemic semantics at the Industry IQ application boundary.

### 2. Keep every claim explicitly hypothetical

`ReasoningHypothesis.claim_status` is fixed to:

```text
hypothesis_only
```

and every `ReasoningContribution` records:

```text
causal_claim_made = false
authority = recommend_only
```

A contributor may propose a mechanism to investigate. It may not silently convert association, recurrence, KPI structure or an LLM-generated explanation into causal truth.

### 3. Bound contributor reads to pre-authorized explicit context

`BoundedReasoningHost` exposes only CEPIO objects that the existing application boundary has already authorized and that the Performance request explicitly supplied.

A contributor cannot use this host to:

- graph-crawl to additional objects;
- call CEPIO Functions;
- invoke provider bindings;
- persist a Decision;
- start a workflow;
- execute an Action.

Attempting to read an object outside the bounded context fails closed.

This is both a security boundary and an explainability boundary: the Decision can identify exactly which explicit context was available to the domain contributor.

### 4. Compose contributions inside the existing Performance Industry IQ service

`PerformanceIndustryIQService` accepts optional reasoning contributors.

The existing sequence remains authoritative:

```text
Performance evidence
  -> governed Business Logic
  -> version-pinned Performance Contract
  -> deterministic deviation
  -> generic Performance reasoning
  -> bounded domain ReasoningContribution(s)
  -> governed Decision proposal
  -> actor/policy-checked Decision persistence
```

Contributions enrich the Decision observations and recommendation but do not change:

- the Performance status;
- the Performance Contract;
- the source subject;
- the Decision type;
- workflow/action authority.

No contributor can set `recommended_action` through this v0.1 path.

### 5. Require an installed Industry IQ pack for each governed contributor

A contributor may declare `required_pack_id`.

`ReasoningContributionEngine` fails closed if the corresponding Industry IQ pack is not installed in the runtime. This keeps reasoning code tied to an explicit, versioned deployment capability rather than allowing arbitrary host-local reasoning to appear silently.

### 6. Reliability is the first domain implementation

The first implementation is:

```text
cepio.iq.reliability.reasoning@0.1.0
```

with contributor:

```text
cepio.reasoning.reliability@0.1.0
```

The Reliability pack depends on:

```text
cepio.iq.performance.response >=0.1.0,<0.2.0
```

and registers no Function, Decision or Action capability.

The contributor consumes only explicitly supplied, authorized Reliability context objects and a small allow-list of properties from:

- `ConditionObservation` / `ConditionSignal`;
- `FailureEvent`;
- `WorkOrder`.

v0.1 can form three deterministic hypothesis families:

1. equipment-condition degradation may be contributing;
2. a recurring/unresolved failure mechanism may be contributing;
3. previous corrective work may not have fully resolved the issue.

Each hypothesis carries supporting/contradicting evidence IDs, explicit uncertainty, and a highest-value next-check candidate where relevant.

### 7. Information gain is guidance, not an autonomous experiment planner

`InformationGainCandidate` describes a question, rationale, evidence needed and priority.

v0.1 does not compute EVPI/EVSI, schedule inspections, query providers automatically or launch diagnostics. The purpose is to make the next uncertainty-reducing step explicit for a human, agent or future governed workflow.

### 8. Intervention options remain recommend-only

`ReasoningInterventionOption` is fixed to:

```text
authority = recommend_only
policy_required = true
```

The options are investigation/intervention candidates, not executable Actions. Converting one into a Kinetic Action or workflow requires a separate governed hand-off.

## Reliability example

For a compressor availability deviation, explicit Reliability context may include:

```text
ConditionObservation: vibration degraded and rising
FailureEvent: repeated bearing-degradation events
WorkOrder: bearing replacement reopened
```

The resulting reasoning can state:

```text
Hypothesis H1: condition degradation may be contributing
Hypothesis H2: recurring unresolved failure mechanism may be contributing
Hypothesis H3: prior corrective work may not have fully resolved the issue

Uncertainty: none of these establishes causal root cause

Information gain:
  - corroborate condition trend independently
  - compare repeated failures by component/mode/regime
  - verify post-maintenance effectiveness
```

The final CEPIO Decision still has:

```text
recommended_action = null
workflow_started = false
action_executed = false
```

## Customer-data boundary

ReasoningContribution does not create a cross-customer learning channel.

Customer-specific objects and evidence remain inside the authenticated runtime/tenant boundary. Contributions are generated for the current request only. The shared CEPIO model is not trained from customer observations, hypotheses or Decision content.

Any future promotion of reusable reasoning patterns across domains/customers must use CEPIO's separate generalization/qualification and human-governed capability-promotion mechanisms, not runtime customer data.

## Compatibility

This change is additive:

- no ontology class/property is changed;
- no stable `/api/v1`, SDK or MCP contract is changed;
- existing `PerformanceIndustryIQService(performance_service, application_service)` construction remains valid;
- deployments with no reasoning contributors behave exactly as before;
- existing Performance Decision type and policy path remain unchanged.

## Validation

Acceptance requires tests proving:

- contribution internal evidence/hypothesis references validate;
- duplicate contributor identity fails closed;
- missing required Industry IQ pack fails closed;
- contributors cannot read outside bounded authorized context;
- Reliability emits hypotheses, uncertainty and information-gain suggestions deterministically from synthetic evidence;
- Performance reasoning remains unchanged when no contributor is configured;
- Reliability enrichment persists through the same governed Decision path;
- no Action audit is created by contribution reasoning or Decision persistence;
- all existing CI, compatibility, security, architecture and domain qualification gates remain green.

## Non-goals

v0.1 does not:

- introduce a general LLM reasoning runtime;
- infer causal truth;
- compute quantitative causal effect;
- compute EVPI/EVSI;
- perform Bayesian or Monte Carlo inference;
- traverse arbitrary customer graphs from a contributor;
- automatically retrieve new provider evidence;
- start inspections, diagnostics or workflows;
- choose or execute a CEPIO Action;
- rank personnel;
- expose ReasoningContribution through stable REST/MCP.

## Next evolution

The next controlled step is to add another independent domain contributor—most naturally Drilling or Refinery—and prove that both can consume the same ReasoningContribution contract without changing Performance truth or Kinetic authority.

After at least two domains qualify against the same contract, CEPIO can consider a governed contributor registry, richer hypothesis/evidence persistence, and protocol exposure through experimental REST/MCP surfaces.
