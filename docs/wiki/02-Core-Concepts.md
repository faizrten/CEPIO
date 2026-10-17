# Core Concepts

## The CEPIO operating model

CEPIO combines three dimensions:

```text
                           CEPIO
                             |
          +------------------+------------------+
          |                  |                  |
      SEMANTICS            STATE             KINETICS
          |                  |                  |
      Objects              Events             Functions
      Relationships        Time               Decisions
      Properties           History            Actions
      Evidence             Provenance         Workflows
      Uncertainty          Projection         Constraints
          |                  |                  |
          +------------------+------------------+
                             |
                      Policy + Audit
```

A cross-cutting decision-learning loop connects these dimensions:

```text
Evidence
   -> Claim / Hypothesis / Assumption
   -> Uncertainty + Confidence
   -> Recommendation / Decision
   -> Action
   -> Outcome
   -> New Evidence
```

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

Relationships may also carry temporal history.

## Property

A **Property** is a typed attribute with canonical meaning.

Properties are not simply copied source columns. Each source field is classified into the canonical property contract, an observation, a relationship key, provenance metadata or a customer-specific extension.

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

## Claim, Hypothesis and Assumption

A **Claim** is an assertion about the enterprise or industrial system.

A **Hypothesis** is a claim that remains subject to evaluation against evidence.

An **Assumption** is a claim explicitly adopted as an input to reasoning, analysis or a decision.

CEPIO keeps these distinct from the underlying physical or business object. For example, a fault interpretation may remain an OSDU object while the claim that the fault is sealing is represented as a CEPIO hypothesis supported or contradicted by evidence.

## Assessment

An **Assessment** is a first-class evaluation about another CEPIO entity. Core 0.3.0 defines three generic assessment types relevant to decision intelligence:

- `UncertaintyAssessment`;
- `ConfidenceAssessment`;
- `InformationGain`.

Assessments inherit normal CEPIO identity, provenance, versioning and bitemporal behavior.

## Uncertainty

An **UncertaintyAssessment** describes incomplete knowledge or variability associated with a subject. CEPIO Core defines the semantic abstraction, not the domain-specific probability model.

Examples of domain characteristics that may be assessed include:

```text
Subsurface -> fault transmissibility, OWC, permeability
Drilling   -> pore pressure, formation top, NPT duration
Refinery   -> feed quality, fouling rate, equipment health
Commercial -> price, demand, schedule
```

The domain defines what is uncertain. Specialized analytical engines may define how it is quantified.

CEPIO therefore does **not** require every uncertainty to be represented as a probability distribution or P10/P50/P90 values. A domain profile may use ranges, categorical alternatives, ensembles, distributions or qualitative states as appropriate.

## Confidence

A **ConfidenceAssessment** describes the strength of belief in an assertion or assessment.

Confidence and uncertainty are related but not interchangeable. A team may have moderate confidence in the claim that a fault is sealing while fault transmissibility itself remains materially uncertain.

## Dependency and correlation

A simple dependency may use the canonical `dependsOn` relationship.

When a dependency must itself carry richer semantics, CEPIO Core provides a reified `Dependency` object with explicit source and target endpoints. This allows later domain profiles or runtimes to attach dependency kind, sensitivity, model provenance or other governed metadata without changing the universal Core.

`correlatedWith` provides a symmetric relationship between uncertainty assessments. CEPIO records correlation semantics; it does not become the numerical sampling engine.

## Information gain

**InformationGain** is the Core semantic anchor for evaluating whether additional information would materially reduce an uncertainty.

A domain Function or external analytical engine may calculate EVPI, EVSI, entropy reduction or another metric and attach the result to the InformationGain assessment.

This supports questions such as:

```text
Would another pressure test materially change the drilling decision?
Would an inspection reduce enough uncertainty to justify its cost?
Would new seismic information change the preferred development option?
```

## Risk versus uncertainty

**Risk** and **uncertainty** are deliberately separate Core concepts.

```text
Uncertainty
    -> creates exposure in a context
    -> may contribute to Risk
    -> may lead to Consequence
```

Uncertainty describes what is not fully known or what may vary. Risk describes the possibility and consequence of an outcome under uncertain conditions.

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
- action execution.

Events can be used to deterministically derive operational state.

## State

**State** is the current or historical condition of an object derived from authoritative facts and/or events.

Example:

```text
TripEvent
   -> CompressorOperatingStateProjector
   -> operatingState = "tripped"

RecoveryEvent
   -> projector
   -> operatingState = "running"
```

## Function

A **Function** performs typed calculation, reasoning or transformation without being treated as an externally consequential action.

Examples:

- calculate production-loss exposure;
- estimate equipment risk;
- compute remaining margin opportunity;
- identify blast radius;
- recommend maintenance priority;
- evaluate or propagate uncertainty using a bound analytical engine.

## Decision

A **Decision** records the evidence, logic and conclusion connecting observed state to a recommended course of action.

Decision remains a Kinetic concept rather than a Core concept so the Core ontology remains the dependency root. Decisions can reference Core evidence, claims, assumptions, uncertainty assessments and confidence assessments.

Decision records are useful because industrial AI should be able to explain not only *what* it recommends, but *why* and under what information state the recommendation was made.

## Action

An **Action** represents a governed operation that changes CEPIO state or invokes an enterprise side effect.

Examples:

- create SAP work order;
- approve inspection plan;
- reschedule a task;
- issue procurement request;
- publish an operating recommendation;
- execute an authorized external workflow.

Actions are subject to authorization, policy, preconditions, idempotency and audit.

## Policy

**Policy** determines what an actor may read, reason over, recommend and execute.

The actor can be a human, application, service identity or AI agent.

## Provenance

**Provenance** explains how CEPIO arrived at a fact or property value.

Typical provenance elements include:

- source system;
- source entity;
- source field;
- source record;
- source-value hash;
- mapping version;
- transformation run;
- observed time;
- ingestion time.

Because uncertainty and confidence assessments are first-class entities, CEPIO can preserve what evidence and assumptions were available when an assessment or historical decision was made.

## Profile

A **Profile** specializes canonical CEPIO semantics for a customer, asset, site or use case without redefining the universal core.

Examples in the repository include profile directions for SATORP/SEO and ARO/AD.

Domain-specific uncertainty characteristics and quantitative representations belong in domain modules or profiles rather than CEPIO Core.

## Binding

A **Binding** maps canonical CEPIO semantics to a technology platform, data product, analytical engine or source system.

Examples:

- Fabric IQ binding;
- SAP adapter mapping;
- PI tag mapping;
- OSDU semantic projection;
- reservoir simulator binding;
- uncertainty propagation service;
- future spatial/3D bindings.
