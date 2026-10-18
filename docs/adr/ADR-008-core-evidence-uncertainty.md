# ADR-008 — Evidence and uncertainty are CEPIO Core semantics

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

Industrial decisions depend on more than deterministic object state. The enterprise must be able to represent what evidence exists, what is believed, what is assumed, what remains uncertain, how strongly a claim is supported, and how uncertainty propagates into later decisions.

This requirement appears across domains:

- subsurface: fault transmissibility, contacts, connectivity, volumetrics and recovery uncertainty;
- drilling: pore pressure, formation-top and NPT uncertainty;
- refinery: feed quality, equipment health and catalyst-state uncertainty;
- maintenance: failure probability and inspection uncertainty;
- commercial planning: demand, price and schedule uncertainty.

If each domain invents its own uncertainty abstraction, CEPIO loses generalization and agents cannot reason consistently across domains.

## Decision

CEPIO Core defines generic epistemic and decision-support semantics. Core 0.3.0 introduces:

- `Evidence`;
- `Claim`;
- `Hypothesis` as a specialization of `Claim`;
- `Assumption` as a specialization of `Claim`;
- `Assessment`;
- `UncertaintyAssessment` as a specialization of `Assessment`;
- `ConfidenceAssessment` as a specialization of `Assessment`;
- `InformationGain` as a specialization of `Assessment`;
- `Dependency` for reified dependency relationships when a simple `dependsOn` edge is insufficient.

Core also defines relationships for evidence support and contradiction, assessment targets, uncertainty/confidence attachment, uncertainty reduction, information gain, reified dependency endpoints, correlation and supersession.

## Boundary

CEPIO Core defines **what uncertainty means in the enterprise operating model**. It does not define domain-specific uncertain variables or numerical solution methods.

Core owns:

```text
Evidence
  -> Claim / Hypothesis / Assumption
  -> UncertaintyAssessment / ConfidenceAssessment
  -> dependency and correlation semantics
  -> InformationGain
```

Domain modules and profiles own vocabulary such as:

```text
subsurface:faultTransmissibility
subsurface:oilWaterContact
refinery:foulingRate
drilling:porePressure
commercial:oilPrice
```

Specialized analytical engines own computation such as:

- Monte Carlo sampling;
- ensemble generation;
- reservoir simulation;
- Bayesian inference;
- distribution fitting;
- uncertainty propagation algorithms;
- EVPI/EVSI calculations.

Those capabilities may be invoked through CEPIO Functions or Runtime Bindings, but their mathematics is not encoded into CEPIO Core.

## Risk remains distinct from uncertainty

`Risk` already exists in CEPIO Core and remains semantically separate.

```text
Uncertainty
    -> creates exposure under a context or decision
    -> may contribute to Risk
    -> may lead to Consequence
```

Uncertainty describes incomplete knowledge or variability. Risk describes the possibility and consequence of an undesirable or beneficial outcome under uncertainty.

## Confidence remains distinct from uncertainty

Confidence concerns strength of belief in an assertion. Uncertainty concerns the range, alternatives or variability associated with a subject.

Example:

```text
Claim: Fault F12 is sealing
ConfidenceAssessment: moderate confidence in the claim
UncertaintyAssessment: fault transmissibility remains poorly constrained
```

Both may coexist and must not be collapsed into one scalar.

## Decision remains Kinetic

`Decision` remains in the Kinetic foundation module. Core does not import Kinetic because Core must remain the dependency root.

This preserves the dependency direction:

```text
Core epistemic semantics
        |
        v
Kinetic decision/action semantics
        |
        v
Domain workflows and agents
```

Kinetic decisions may reference Core evidence, claims, assumptions and assessments through ordinary CEPIO relationships and runtime objects.

## Temporal and provenance consequence

Assessments are first-class CEPIO entities and therefore inherit normal CEPIO identity, provenance, versioning and bitemporal behavior.

This allows CEPIO to reconstruct the information state that existed when a historical decision was made and to distinguish later evidence from evidence available at decision time.

`supersedes` provides a generic semantic link between successive assessments or claims. It does not replace CEPIO object history; it expresses an explicit domain-level replacement relationship when needed.

## Information value

`InformationGain` provides the generic semantic anchor for evaluating whether acquiring additional information may reduce a material uncertainty.

Core does not prescribe how information value is quantified. A domain Function may compute EVPI, EVSI, entropy reduction or another metric and attach the result to an `InformationGain` assessment.

## Consequences

### Positive

- uncertainty semantics generalize across all CEPIO domains;
- domain modules stay smaller and avoid duplicating epistemic primitives;
- agents can distinguish evidence, assumptions, uncertainty, confidence and risk;
- historical decision provenance can preserve the information state available at the time;
- Runtime Bindings can delegate numerical uncertainty computation to specialized engines without losing semantic consistency.

### Costs

- domains must map their own uncertain characteristics into Core assessments;
- applications must avoid treating all assessments as scalar probabilities;
- correlation/dependency graphs require governance to avoid unsupported causal claims;
- richer quantitative contracts will require later profile or runtime specifications.

## Non-goals for Core 0.3.0

This decision does not introduce:

- a probability-distribution schema;
- P10/P50/P90-specific fields;
- stochastic sampling services;
- a Bayesian network engine;
- a Monte Carlo engine;
- Value-of-Information calculation code;
- subsurface-specific semantics;
- automatic causal inference.

Those are subsequent domain/runtime concerns built on this Core contract.

## Validation refresh

Before merge, this contract is revalidated against the current `main` branch so that the Core 0.3.0 additive semantics must pass the repository's current CI, governance, quality, security and compatibility gates rather than relying only on the original qualification run.
