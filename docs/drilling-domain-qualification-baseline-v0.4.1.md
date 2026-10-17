# Drilling Contractor Domain Qualification — baseline v0.4.1

## Result

The first normalized domain-qualification run executes 15 frozen questions across three challenge bands:

- 5 enterprise competency questions;
- 5 operational-optimization questions;
- 5 agentic-operating questions.

Result against the current CEPIO ontology:

- **11 PASS**
- **0 PARTIAL**
- **4 FAIL**
- **0 ERROR**
- **75.0% semantic capability coverage**

The raw v0.4 and normalized v0.4.1 packs produce the same 11/4 result. v0.4.1 corrects the benchmark's initial `core:Decision` namespace assumption to the existing CEPIO `kinetic:Decision` abstraction and then sharpens the four failed competencies around the actual missing semantics. Therefore the four failures are not artifacts of that benchmark error.

## What already passes

All five enterprise questions pass the current semantic-capability harness:

1. fleet / contract / customer economic exposure;
2. recurring fleet loss and accountable intervention;
3. downtime-to-cash and margin scenario context;
4. contract portfolio decision context;
5. capital-allocation context across reliability, performance and commercial exposure.

Four of five operational-optimization questions also pass:

- invisible-lost-time comparison;
- parameter / dysfunction context;
- recurring-event learning loop;
- normalized rig / crew peer performance.

The only optimization failure is predictive NPT risk, because CEPIO cannot yet represent model-derived prediction as a governed inference distinct from observed enterprise fact.

Three of five agentic questions pass at semantic level:

- supply-chain / procurement intervention;
- contract-claim evidence context;
- the existing agent / decision / authority primitives used by those compositions.

The remaining agentic gaps are evidence grounding, governed plan revision and outcome/value attribution.

## Four accepted architecture gaps for review

### DQ-009 — Prediction / inference semantics

CEPIO needs a reusable representation for a model-derived prediction with explicit operating scope, risk/outcome, horizon and provenance. A prediction must not silently become observed state.

Recommended ownership: `agentic_operations` / common CEPIO semantics.

### DQ-011 — Recommendation supported by evidence

CEPIO already contains `agentic:Recommendation`, `agentic:ControlPoint`, `kinetic:Decision` and workforce authority semantics. The missing semantic is the explicit statement of which enterprise evidence supports the recommendation.

Recommended ownership: `agentic_operations`.

### DQ-014 — Operational plan and governed revision

This confirms an earlier drilling-persona finding. A drilling-only `ProgramDeviation` was correctly rejected; CEPIO now needs the common replacement: operational plan + plan revision + authorizing decision, with authority resolved independently.

Recommended ownership: `kinetic` / common work-and-decision semantics.

### DQ-015 — Outcome / value attribution

CEPIO can record decisions and KPI observations, but cannot yet state that a governed intervention was assessed against an operating outcome with risk/safety context. The abstraction should work for AI interventions and conventional operational-improvement actions.

Recommended ownership: `performance`.

## Architectural interpretation

The result is stronger than a 75% headline suggests.

No new drilling-specific canonical concept is required by this qualification slice. The four failures are all **CORE reusable operating abstractions**. This means the drilling domain itself is no longer primarily constrained by drilling vocabulary; it is now stressing CEPIO's cross-industry decision, inference, governance and value-realization model.

That is the desired behavior of the Generalization Lab: a mature domain should increasingly improve the common operating abstraction rather than accumulate domain nouns.

## Next remediation order

1. prediction / inference object and operating scope;
2. evidence support for recommendations / decisions;
3. common operational-plan and plan-revision semantics;
4. outcome-assessment / value-attribution semantics;
5. rerun normalized v0.4.1 without changing the benchmark;
6. once semantic readiness is achieved, build deterministic runtime fixtures for the four new capabilities;
7. extend operational-assurance gates for stale predictions, unsupported recommendations, unauthorized plan revisions and unproven value claims;
8. proceed to cross-customer qualification.

Machine-readable decisions are recorded in `generalization/gaps/drilling-contractor-domain-qualification-v0.4.1.yaml`.

## Cost-inclusive successor v0.4.2

The frozen v0.4 contract and its normalized v0.4.1 result remain unchanged. Successor v0.4.2 strengthens `DC-DQ-003` by requiring `CostRecord` alongside contract rate, downtime and revenue, with `rateForContract`, `revenueFor` and `costFor` links to `DrillingContract`. This makes cost semantics part of the competency composition rather than relying on the question text alone. The v0.4.2 contract is generated and evaluated separately by the qualification workflow.
