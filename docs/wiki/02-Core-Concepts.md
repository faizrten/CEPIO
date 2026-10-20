# Core Concepts

## Core vs Industry IQ

CEPIO now distinguishes between a deliberately **thin operating Core** and the **thick Industry IQ** built above it.

Core answers questions such as:

- What industrial object/relationship/state does this mean?
- What evidence supports it?
- When was it true and when was it known?
- What uncertainty/confidence exists?
- What Decision/Action/authority semantics apply?

Industry IQ packages reusable industrial competence such as Skills, competency questions, failure/risk patterns, performance logic, decision patterns, workflows and assurance contracts.

Runtime control-plane mechanisms such as the Capability Registry, Memory, Retrieval & Indexing and Compiled Industry IQ govern how that competence is admitted/selected/activated; they are **not automatically new ontology primitives**.

The governing product rule is:

> **Thin infrastructure. Thick Industry IQ.**

## The CEPIO operating model

CEPIO combines three semantic/runtime dimensions:

```text
                           CEPIO
                             |
          +------------------+------------------+
          |                  |                  |
      SEMANTICS            STATE             KINETICS
          |                  |                  |
      Objects              Events             Functions
      Relationships        Time               Opportunities
      Properties           History            Decisions
      Evidence             Provenance         Actions
      Uncertainty          Projection         Workflows
          |                  |                Constraints
          +------------------+------------------+
                             |
                      Policy + Audit
```

A cross-cutting decision-learning loop connects these dimensions:

```text
Evidence
   -> Claim / Hypothesis / Assumption
   -> Uncertainty + Confidence
   -> Opportunity
   -> Options
   -> Recommendation
   -> Decision
   -> Action
   -> Outcome
   -> New Evidence
```

"New Evidence" supports evaluation and future governed learning. It does **not** mean customer operational data silently trains or mutates global CEPIO Industry IQ.

## Object

An **Object** represents a durable thing the enterprise cares about.

Examples:

- compressor;
- process unit;
- well;
- rig;
- work order;
- supplier;
- contract;
- organization;
- project;
- material;
- KPI;
- risk.

Objects have stable CEPIO identity even if identifiers in source systems change.

## Relationship

A **Relationship** connects objects using typed industrial semantics.

Examples:

```text
Compressor --installedIn--> Hydrocracker
Compressor --hasWorkOrder--> WorkOrder
Pump --drivenBy--> Motor
ProcessUnit --produces--> Product
WorkOrder --requires--> SparePart
Supplier --supplies--> SparePart
```

Relationships may carry temporal history.

## Property

A **Property** is a typed attribute with canonical meaning.

Properties are not simply copied source columns. Each source field is classified into the canonical property contract, an observation, a relationship key, provenance metadata or a customer/profile-specific extension.

## Evidence

**Evidence** is a first-class CEPIO Core object representing information used to support, contradict or update a claim, hypothesis, assumption or assessment.

Evidence can bind to source-system records, measurements, documents, models or other governed objects without requiring CEPIO to copy the underlying technical data.

Examples include:

- a pressure measurement;
- an inspection result;
- a laboratory analysis;
- a seismic or reservoir-model result referenced from OSDU;
- a work-order history;
- a commercial forecast;
- a validated engineering calculation.

Evidence must remain distinct from generated prose/model output.

```text
Model Output != Evidence
```

## Claim, Hypothesis and Assumption

A **Claim** is an assertion about the enterprise or industrial system.

A **Hypothesis** is a claim that remains subject to evaluation against evidence.

An **Assumption** is a claim explicitly adopted as an input to reasoning, analysis or a Decision.

CEPIO keeps these distinct from the underlying physical/business object. For example, a fault interpretation may remain an OSDU object while the claim that the fault is sealing is represented as a CEPIO hypothesis supported/contradicted by evidence.

## Assessment

An **Assessment** is a first-class evaluation about another CEPIO entity. Current Core includes generic assessment types relevant to decision intelligence:

- `UncertaintyAssessment`;
- `ConfidenceAssessment`;
- `InformationGain`.

Assessments inherit normal CEPIO identity, provenance, versioning and bitemporal behavior.

## Uncertainty

An **UncertaintyAssessment** describes incomplete knowledge or variability associated with a subject. CEPIO Core defines the semantic abstraction, not the domain-specific probability model.

Examples:

```text
Subsurface -> fault transmissibility, OWC, permeability
Drilling   -> pore pressure, formation top, NPT duration
Refinery   -> feed quality, fouling rate, equipment health
Commercial -> price, demand, schedule
```

The domain defines what is uncertain. Specialized analytical engines may define how it is quantified.

CEPIO does not require every uncertainty to be represented as a probability distribution or P10/P50/P90 values. Profiles/domain models may use ranges, categorical alternatives, ensembles, distributions or qualitative states.

## Confidence

A **ConfidenceAssessment** describes the strength of belief in an assertion/assessment.

Confidence and uncertainty are related but not interchangeable. A team may have moderate confidence that a fault is sealing while fault transmissibility itself remains materially uncertain.

## Dependency and correlation

A simple dependency may use canonical `dependsOn`.

When a dependency must itself carry richer semantics, CEPIO Core provides a reified `Dependency` object with explicit source/target endpoints, enabling domain/runtime attachment of dependency kind, sensitivity/model provenance or other governed metadata without changing universal Core.

`correlatedWith` provides a symmetric relationship between uncertainty assessments. CEPIO records correlation semantics; it does not become the numerical sampling engine.

## Information gain

**InformationGain** is the Core anchor for evaluating whether additional information would materially reduce uncertainty.

A domain Function/external analytical engine may calculate EVPI, EVSI, entropy reduction or another metric and attach the result to the assessment.

Examples:

```text
Would another pressure test materially change the drilling Decision?
Would an inspection reduce enough uncertainty to justify its cost?
Would new seismic information change the preferred development option?
```

## Risk versus uncertainty

**Risk** and **uncertainty** are deliberately separate.

```text
Uncertainty
    -> creates exposure in context
    -> may contribute to Risk
    -> may lead to Consequence
```

Uncertainty describes incomplete knowledge/variability. Risk describes possibility and consequence of an outcome under uncertain conditions.

## Event

An **Event** is an immutable occurrence.

Examples:

- trip;
- start;
- shutdown;
- inspection;
- anomaly detection;
- work-order completion;
- material receipt;
- approval;
- Action execution.

Events can deterministically contribute to derived operational state.

## State

**State** is the current/historical condition of an object derived from authoritative facts and/or events.

Example:

```text
TripEvent
   -> CompressorOperatingStateProjector
   -> operatingState = "tripped"

RecoveryEvent
   -> projector
   -> operatingState = "running"
```

State is temporally governed: valid time and transaction time must remain distinguishable.

## Function

A **Function** performs typed calculation, reasoning or transformation without being treated as an externally consequential Action.

Examples:

- calculate production exposure;
- estimate equipment risk;
- compute remaining margin opportunity;
- identify blast radius;
- evaluate maintenance priority;
- evaluate/propagate uncertainty through a bound analytical engine.

## Opportunity, Option and Recommendation

An **Opportunity** is a Kinetic object representing a prospective actionable situation in which one or more courses of action could advance an Objective or avoid loss.

An **Option** is one possible course of action evaluated within an Opportunity/Decision context.

A **Recommendation** is a reasoned proposal favoring one or more Options. It is deliberately not a Decision: an AI agent, engineer or analytical workflow may recommend without possessing selection/execution authority.

```text
Objective
   <- opportunityForObjective - Opportunity
                                  |
                                  +-- hasOption --------> Option A
                                  +-- hasOption --------> Option B
                                  +-- hasOption --------> Option C
                                  |
                                  +-- hasRecommendation -> Recommendation
                                                              |
                                                              +-- recommendsOption -> Option B

Decision
   -- addressesOpportunity --> Opportunity
   -- selectedOption --------> Option B
   -- basedOnRecommendation -> Recommendation
```

Opportunity belongs in Kinetic rather than generic Core because it is prospective/action-oriented. Domains specialize what an Opportunity concerns and may attach domain-specific maturity/value/feasibility/ranking semantics through domain modules, profiles or bound analytical models.

Examples:

```text
Subsurface  -> infill-well opportunity
Refinery    -> margin-improvement opportunity
Reliability -> intervention opportunity
Drilling    -> performance-improvement opportunity
Commercial  -> contracting / portfolio opportunity
```

## Decision

A **Decision** records the evidence, logic, authority context and conclusion connecting observed state to a selected course of action.

Decision remains a Kinetic concept. Decisions can reference Evidence, claims, assumptions, uncertainty/confidence assessments, Opportunities, Options and Recommendations.

Industrial AI should be able to explain not only *what* it recommends, but *why*, under what information state and who had authority to select the option.

## Action

An **Action** represents a governed operation that changes CEPIO state or invokes an enterprise side effect.

Examples:

- create SAP work order;
- approve inspection plan;
- reschedule a task;
- issue procurement request;
- execute an authorized external workflow.

Actions are subject to authenticated authority, policy, preconditions, idempotency, audit and — for external effects — verification/reconciliation.

## Outcome

An **Outcome** represents the verified terminal result/consequence of a governed intervention rather than assuming that dispatch equals success.

A workflow/external Action may therefore preserve:

```text
Decision -> Action -> source execution -> verification/reconciliation -> Outcome
```

Outcome evidence can be used for assurance and subsequent evaluation while remaining separate from customer-data training/global knowledge promotion.

## Policy and authority

**Policy** determines what an actor may read, reason over, recommend, decide and execute.

The actor can be a human, application, service workload or AI agent.

The core boundary is:

```text
Knowledge != Authority
Recommendation != Execution
```

## Provenance

**Provenance** explains how CEPIO arrived at a fact/property/state/evidence assertion.

Typical elements include:

- source system;
- source entity/record;
- source field/value hash;
- mapping version;
- transformation run;
- observed time;
- ingestion/transaction time.

Because uncertainty, confidence, Opportunity, Recommendation, Decision and Outcome are explicit entities/contracts, CEPIO can preserve what evidence and assumptions existed when an intervention was selected and what happened afterward.

## Profile

A **Profile** specializes CEPIO semantics/operating knowledge for a customer, asset, site or deployment without redefining universal Core.

Customer-specific uncertainty models, thresholds, formulas, procedures, target definitions and source bindings belong in domain/profile/private Industry IQ unless independent evidence justifies reusable promotion.

## Binding

A **Binding** maps CEPIO industrial contracts to a technology platform, source system, analytical engine or data product while preserving authoritative source ownership.

Examples:

- Fabric/Fabric IQ binding;
- SAP EAM binding;
- PI/historian mapping;
- OSDU semantic/evidence projection;
- Cognite provider binding;
- reservoir-simulator/uncertainty-engine binding;
- spatial/3D binding.

The Binding Contract should preserve CEPIO identity, evidence/provenance and governed external-action verification rather than exposing provider schemas as application truth.

## Runtime control-plane concepts

Some current CEPIO capabilities are product/runtime contracts rather than canonical ontology classes.

### Capability Registry

Records evidence-backed claims about what CEPIO can support and where that capability has been qualified.

### Industry IQ Pack Registry

Resolves reusable deployable Industry IQ packages/version/dependencies.

### Skill Registry

Admits/binds procedures and determines whether a Skill is READY in a concrete runtime/actor context.

### Memory

Stores durable reusable or tenant/profile-scoped knowledge/evidence references separately from per-task working context.

### Retrieval & Indexing

Selects bounded task-relevant candidate evidence/memory through governed capability routing. Indexes are projections, not truth.

### Compiled Industry IQ

Deterministically compiles reusable capability records into bounded runtime bundles/cache acceleration. Cache state is not authority.

### Management Contract

Provides a separate read-oriented control-plane projection over sanitized runtime capabilities/health; it is not a domain ontology primitive or Action authority surface.

## Performance Contracts

Performance intelligence spans semantic concepts and contract/runtime specialization.

Reusable ontology semantics provide generic Objective, KPI, Evidence, Outcome and relationship vocabulary. Performance Contracts define organization-neutral/reference or customer-specialized structures such as:

- objectives / KRs / KPIs;
- targets/thresholds/guardrails;
- accountability;
- contribution/driver relationships;
- governed response bindings.

Industry Performance Reference Packs can provide reusable operating-model hypotheses while customer formulas/targets/scopes remain customer-owned specialization.

## Final Core design rule

A useful concept is not automatically a Core ontology concept.

When new industrial knowledge appears, decide explicitly whether it belongs in:

```text
CORE
DOMAIN
MAPPING
PROFILE
REJECT
```

or in a runtime/Industry-IQ contract rather than the ontology at all.

The success criterion is not class count. It is **reusable industrial competency with stable semantics and governed evidence/actionability**.
