# CEPIO Production Technologist v0.2

## Scope

This slice extends the qualified Production Technologist v0.1 spine with three executable journeys:

- **PROD-03 — Production Optimization & Constraint Allocation**
- **PROD-04 — Artificial Lift Performance & Optimization**
- **PROD-05 — Well Integrity & Operating Envelope Assurance**

The cumulative v0.2 gate therefore executes PROD-01 through PROD-06, with PROD-07 through PROD-10 remaining frozen future coverage.

## Architectural rule

CEPIO does not become a nodal, network or artificial-lift simulator. External engineering sensitivities are treated as versioned evidence. CEPIO owns the reasoning context around objectives, constraints, options, uncertainty, recommendation, authority and downstream learning.

No new production ontology classes are introduced in v0.2. The journeys reuse the existing Production v0.1 semantics plus Core and Kinetic primitives.

## Synthetic P-118 optimization case

The v0.2 benchmark extends the existing synthetic P-118 case. It evaluates operating choices against three active constraints:

1. maximum governed drawdown = **58 bar**;
2. lift-gas allocation cap = **1.85 MMscf/d**;
3. minimum attainable backpressure without reconfiguration = **14 bar**.

The options deliberately create four decision classes:

- `OPT-GL-18`: feasible;
- `OPT-BP-14`: feasible and recommended;
- `OPT-COMB-18-14`: higher uplift but only 0.5 bar drawdown margin, therefore conditional/review-required;
- `OPT-PUSH-20-12`: highest theoretical uplift but violates current hard constraints and is rejected.

This prevents CEPIO from equating maximum theoretical production with the correct operating recommendation.

## PROD-04 artificial lift

A versioned external gas-lift sensitivity is used as evidence. CEPIO calculates only comparison metrics such as marginal response; it does not solve lift hydraulics. The current synthetic field allocation cap makes 1.8 MMscf/d the candidate for an **authorized monitored test**, while the unconstrained external model optimum is 2.0 MMscf/d.

## PROD-05 operating envelope

Each operating option is evaluated against the authoritative well operating envelope. Outcomes are classified as:

- `within`;
- `within_reduced_margin_requires_review`;
- `violates_hard_limit`.

CEPIO may recommend escalation or reject an option under the current envelope. It may not approve an integrity exception, alter the envelope, or execute the operating change.

## Authority

The `production_technologist` policy remains recommendation-only. v0.2 adds read access to Kinetic `Opportunity`, `Option`, and `OptionRecommendation` so option reasoning can be admitted through Skill preflight, while actions/functions/decisions remain empty.

## Acceptance gate

```text
PROD-01 ANSWERED
PROD-02 ANSWERED
PROD-03 ANSWERED
PROD-04 ANSWERED
PROD-05 ANSWERED
PROD-06 ANSWERED
Blocked 0
```

Additional fail-closed checks cover unauthorized actors and missing external source/version identity.
