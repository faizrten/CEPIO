# ADR-009 — Opportunity as a universal Kinetic primitive

## Status

Accepted for CEPIO Kinetic 0.3.0.

## Context

Industrial operating decisions commonly begin before a formal decision exists. Teams and agents first identify a prospective situation where value can be created, loss can be avoided, risk exposure can be reduced, or an objective can be advanced.

Examples include:

- a subsurface infill-well opportunity;
- a refinery margin-improvement opportunity;
- a maintenance intervention opportunity;
- a drilling performance opportunity;
- a supply-chain optimization opportunity.

If each domain defines its own incompatible opportunity concept, CEPIO loses the ability to compare, prioritize, govern and learn across domains.

Opportunity is not purely epistemic. Evidence and uncertainty describe what the enterprise knows. Opportunity describes something the enterprise may choose to pursue. It therefore belongs in the Kinetic foundation rather than Core.

## Decision

CEPIO Kinetic defines three universal prospective decision concepts:

- `kin:Opportunity` — a prospective, actionable situation in which one or more options could advance an objective or avoid loss;
- `kin:Option` — a possible course of action evaluated in an opportunity or decision context;
- `kin:OptionRecommendation` — an authority-neutral proposal favoring one or more options without constituting the authoritative decision.

The existing `kin:Decision` remains the authoritative selection/conclusion record.

`OptionRecommendation` is deliberately named distinctly from the established `agentic:Recommendation`. The repository already exposes that local name, so introducing a second canonical `Recommendation` IRI would make unqualified type resolution ambiguous. Kinetic 0.3 therefore introduces the reusable authority-neutral primitive without silently changing the established agentic contract. Consolidating or migrating the agentic type, if desired, requires a separate compatibility-controlled semantic migration.

The minimum universal relationships are:

```text
Opportunity --opportunityForObjective--> Objective
Opportunity --hasOption---------------> Option
Opportunity --hasRecommendation-------> OptionRecommendation
OptionRecommendation --recommendsOption--> Option
Decision --addressesOpportunity-------> Opportunity
Decision --selectedOption-------------> Option
Decision --basedOnRecommendation------> OptionRecommendation
```

Core evidence and uncertainty semantics attach through existing generic Core relationships rather than Kinetic-specific duplicates:

```text
Opportunity --hasEvidence--------------> Evidence
Opportunity --hasUncertaintyAssessment-> UncertaintyAssessment
Opportunity --hasAssumption------------> Assumption
Opportunity --hasHypothesis------------> Hypothesis
```

## Consequences

### Positive

1. Domain modules can represent opportunities consistently without defining parallel decision vocabularies.
2. CEPIO can rank and govern opportunities across subsurface, drilling, refinery, maintenance and commercial contexts.
3. The universal option recommendation remains explicitly distinct from Decision, preserving human/agent authority boundaries.
4. Opportunity can participate directly in evidence, uncertainty and confidence graphs without moving prospective semantics into Core.
5. The same decision-learning loop can be reused across domains:

```text
Evidence
  -> Understanding
  -> Uncertainty
  -> Opportunity
  -> Options
  -> OptionRecommendation
  -> Decision
  -> Action
  -> Outcome
  -> New Evidence
```

### Constraints

1. `Opportunity` must not become a synonym for `Risk`. Risk concerns adverse uncertainty/consequence; an Opportunity is an actionable prospective path toward an objective, including avoided loss.
2. `Opportunity` must not imply approval or authority to act.
3. `OptionRecommendation` must not be modeled as a subclass of `Decision`.
4. Domain modules should specialize what an opportunity concerns, not redefine the universal opportunity/option/decision lifecycle.
5. Domain-specific value metrics, maturity schemes, ranking models and economics remain domain/profile/runtime concerns unless later promoted through generalization evidence.
6. Existing `agentic:Recommendation` compatibility is preserved in Kinetic 0.3; any later consolidation into the Kinetic primitive requires an explicit migration contract rather than ambiguous duplicate local names.

## Subsurface application

For the first Subsurface reference slice:

```text
Opportunity: Develop remaining hydrocarbons in Reservoir R3

Options:
  P-117
  P-118
  P-121

Evidence:
  OSDU wells, logs, seismic, interpretations and reservoir-model scenarios

Uncertainty:
  fault transmissibility, connectivity, aquifer strength, contacts

OptionRecommendation:
  P-118

Decision:
  select / defer / reject an option under governed authority
```

The OSDU/ADME objects remain authoritative technical records. CEPIO owns the cross-domain prospective decision semantics.
