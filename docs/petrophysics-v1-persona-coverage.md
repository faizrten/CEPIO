# CEPIO Petrophysics v1 Persona Coverage

## Milestone

**CEPIO Petrophysics v1 Persona Coverage** proves depth for one Subsurface persona family before broadening to additional disciplines or live-source integration.

The milestone covers eight Petrophysics journeys:

| ID | Journey | Role |
|---|---|---|
| PET-01 | Data Readiness & Log QC | Horizontal readiness layer |
| PET-02 | Formation Evaluation Assurance | Anchor executable journey |
| PET-03 | Saturation & Fluid Contact Uncertainty | Primary |
| PET-04 | Core–Log Integration & Rock Typing | Primary |
| PET-05 | Cross-Well Interpretation Consistency | Primary |
| PET-06 | Model Handover & Property Propagation | Primary |
| PET-07 | Remaining Hydrocarbon & Opportunity Support | Supporting → primary |
| PET-08 | New Well Learning & Appraisal Update | Primary |

The design goal is not eight applications. It is one shared Petrophysics intelligence layer expressed through eight repeatable reasoning patterns.

## Architecture

```text
                    PETROPHYSICS PERSONA
                            |
                            v
                Petrophysics Assurance
                            |
        +-------------------+-------------------+
        |                   |                   |
     Evidence           Assumptions         Methods
        |                   |                   |
        +-------------------+-------------------+
                            |
                            v
                    Technical Belief
                            |
              +-------------+-------------+
              |             |             |
         Uncertainty    Confidence    Consistency
              |             |             |
              +-------------+-------------+
                            |
                            v
                  Downstream dependency
                            |
          +-----------------+------------------+
          |                 |                  |
       Geomodel          Reserves          Opportunity
          |                                    |
          v                                    v
     Reservoir Model                         Decision
                            |
                            v
                         Learning
```

CEPIO does not replace the technical systems underneath this graph. OSDU/ADME, interpretation environments and other source systems remain authoritative for technical records and bulk payloads.

## Shared semantic spine

The milestone deliberately reuses existing CEPIO primitives.

### Core

Evidence, Claim, Hypothesis, Assumption, Assessment, UncertaintyAssessment, ConfidenceAssessment, InformationGain and Dependency.

### Kinetic

Opportunity, Option, OptionRecommendation and Decision.

### Thin Subsurface assurance semantics

Petrophysics v1 adds only the domain abstractions required to express persona-level assurance: `PetrophysicsAssuranceCase`, `FormationEvaluationCase`, `DataReadinessAssessment`, `SaturationContactAssessment`, `InterpretationConsistencyAssessment`, `ModelHandoverTrace`, `RemainingHydrocarbonAssessment` and `NewWellLearningAssessment`.

Technical well/log/sample/model records remain external.

## PET-01 — Data Readiness & Log QC

Golden question: **Is the available evidence fit for the formation-evaluation and assurance questions we need to answer, and what is missing?**

The v1 benchmark intentionally gives different evidence completeness to A-11, A-14, A-17 and A-22. CEPIO returns missing evidence explicitly and does not infer or invent source records. PET-01 acts as a horizontal gate for all other journeys.

## PET-02 — Formation Evaluation Assurance

PET-02 remains the anchor runtime delivered in v0.2. It resolves the authoritative A-17 Zone-B interpretation, explains revision delta, preserves source/version provenance, surfaces core/log contradiction, exposes uncertainty/confidence and traces downstream impact. The v1 coverage runtime delegates PET-02 to the existing executable contract rather than reimplementing it.

## PET-03 — Saturation & Fluid Contact Uncertainty

The synthetic portfolio contains four well interpretations. A-22 intentionally diverges in methodology, saturation and contact. PET-03 exposes reservoir contact consensus, uncertainty range, material assumptions, well-level disagreement and downstream reserves/FDP/opportunity/decision sensitivity. The runtime does not calculate a new petrophysical solution; it reasons over the resolved evidence package.

## PET-04 — Core–Log Integration & Rock Typing

RT-2 is designed to reconcile. RT-3 deliberately contains a material permeability contradiction. CEPIO preserves the contradiction and recommends technical review of the transform rather than silently averaging values.

## PET-05 — Cross-Well Interpretation Consistency

A canonical profile is used only as an assurance baseline, not as a forced normalization rule. The runtime flags method divergence, Rw divergence, porosity cutoff divergence, saturation cutoff divergence, stale/non-approved permeability transforms and downstream impact targets. CEPIO never rewrites source interpretations automatically.

## PET-06 — Model Handover & Property Propagation

The reference trace includes A-17 authoritative interpretation, PHIE upscaling from 0.178 to 0.163, rock-type propagation, permeability-transform identity, SM18 → RM21 → forecast lineage, and a deliberate stale A-14 dependency still consuming `K_TRANSFORM_V4`. This journey proves cross-discipline lineage rather than Petrophysics-only retrieval.

## PET-07 — Remaining Hydrocarbon & Opportunity Support

PET-07 connects the epistemic layer to Kinetic semantics:

```text
Petrophysics evidence
      |
      v
RemainingHydrocarbonAssessment
      |
      v
Opportunity
      |
      +--> Recompletion
      +--> Sidetrack
      +--> Infill
      +--> Defer / acquire information
```

The Petrophysics runtime recommends an option but cannot make the investment decision.

## PET-08 — New Well Learning & Appraisal Update

The benchmark stores explicit prior and posterior belief states for porosity, saturation, net pay and fluid contact. CEPIO computes the belief delta, exposes hypothesis updates, identifies high-value evidence and traces downstream contexts that should be reviewed.

```text
Prior belief
   |
New evidence
   |
Posterior belief
   |
Information gain
   |
Model / reserves / opportunity update
```

## Persona authority

The persona family has three conceptual operating profiles: Petrophysicist, Principal Petrophysicist and Petrophysics Technical Authority. The v1 runtime intentionally exposes only the practitioner read/reason/recommend path. It does not expose an autonomous approval action for the Technical Authority.

AI/runtime prohibitions remain: no autonomous declaration of authoritative interpretation, no reserves approval, no external-record overwrite and no investment/well approval.

## Synthetic benchmark

`generalization/benchmarks/subsurface-petrophysics-v1-portfolio.yaml` is CEPIO-authored synthetic data. It is not a real field dataset, an operator benchmark, an empirical calibration set, a reserves basis, or suitable for engineering or investment decisions. It exists to test semantic/runtime behavior reproducibly.

## Runtime

Run all persona journeys:

```bash
PYTHONPATH=src python scripts/run_petrophysics_v1.py --fail-on-blocked
```

Run one journey:

```bash
PYTHONPATH=src python scripts/run_petrophysics_v1.py --journey PET-06 --fail-on-blocked
```

The milestone passes only when `Answered = 8`, `Blocked = 0`, and all skill preflights are READY for the governed `petrophysicist` role.

## What v1 proves

Petrophysics v1 is successful if one shared CEPIO architecture can answer multiple discipline questions without adding scenario-specific data silos. It tests the product thesis:

> **Ontology → shared reality; Journey → reasoning process; Persona → experience; Skill → intelligence; Policy → authority.**

## What comes after v1

Only after this depth milestone is green should Petrophysics move to live source binding. That next phase should replace synthetic source resolution with OSDU/ADME and customer-system capability adapters while preserving these exact reasoning and answer contracts.
