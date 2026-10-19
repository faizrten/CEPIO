# Drilling Contractor Industry IQ scenarios v0.6

## Purpose

CEPIO's drilling semantic and runtime qualification is broader than its executable Industry IQ. The v0.6 scenario map closes that gap deliberately: executable packs should represent how a drilling contractor prepares, executes, protects, improves and monetizes rig operations without turning CEPIO Core into a drilling application or an integration platform.

The governing product loop is:

```text
READINESS
Can we execute?
    |
    v
PERFORMANCE
Are we executing well?
    |
    v
NPT
What went wrong?
    |
    v
RELIABILITY
Will it happen again?
    |
    v
COMMERCIAL
What did it cost / what are we entitled to?
    |
    v
GOVERNED ACTION
What should we do now, who may approve it, and was the outcome verified?
```

## Scenario portfolio

The frozen machine-readable portfolio is `generalization/industry-iq/drilling-contractor-scenarios-v0.6.yaml`.

Priority order:

1. Rig Readiness IQ — executable in this increment.
2. NPT IQ — already executable.
3. Reliability IQ.
4. Drilling Performance IQ.
5. Commercial and Contract IQ.
6. Well Control IQ.
7. Critical Spares IQ.
8. Workforce and Competency IQ.
9. Rig Move IQ.
10. HSE and Barrier IQ.
11. Program Execution IQ.
12. Fleet Allocation IQ.
13. Claims and Invoice Assurance IQ.
14. Service Delivery IQ.
15. Lessons Learned IQ.
16. Capital Allocation IQ.

## Rig Readiness IQ v0.1

The first expansion pack is `cepio.iq.drilling.rig-readiness`.

It answers:

> Can this rig execute the planned operation, and what evidence-backed constraints prevent release?

Readiness is **derived**, not stored as a canonical rig boolean or score. The pack composes existing CEPIO semantics across four evidence dimensions:

### Equipment

- required equipment must resolve as industrial `Equipment`;
- normalized equipment state must be ready/available/operational or explicitly degraded;
- active work orders require a normalized `readinessBlocking` interpretation;
- a blocking work order produces a critical readiness blocker;
- an active work order whose readiness impact is unknown also blocks release rather than being silently ignored.

### Well control

- `WellControlTest` evidence must be linked to tested equipment;
- the test must have a passing normalized state;
- the test must carry a time-zone-aware validity horizon;
- an expired or unscoped test blocks readiness.

This is an assurance decision only. The pack does not autonomously command well-control equipment or perform safety-critical physical actions.

### Workforce

- a `CrewAssignment` must be scoped to the planned activity;
- the assignment must resolve assigned personnel;
- declared `CompetencyRequirement` evidence must be supported by a `CompetencyAssessment` for the assigned person;
- certification alone is not treated as proof of competence.

### Supply

- required materials must carry a normalized readiness state and material number;
- an `InventoryPosition` must match the material, show no shortfall and be stocked at the assessed rig;
- missing stock evidence is a blocker rather than an inferred availability claim.

## Output contract

`assessRigReadiness` returns:

- `READY` — no evidence-backed blockers;
- `CONDITIONALLY_READY` — advisory constraints exist but no critical blocker;
- `NOT_READY` — at least one critical blocker or evidence gap prevents a release claim.

The result includes dimension-level status, explicit blocker codes/messages and the evidence object IDs used in the assessment. It deliberately does not emit a synthetic percentage readiness score.

## Governed kinetic path

The pack also registers:

- decision: `rig-readiness-intervention-recommendation`;
- action: `CreateReadinessException`.

The recommendation may identify follow-up such as a work order, inspection, competency verification, material expedite request or readiness exception. `CreateReadinessException` requires an authorized human role and human approval. It creates a generic governed `WorkItem` linked to the rig and planned activity; no new canonical `ReadinessConstraint` class is introduced.

## North Star boundaries

1. CEPIO Core remains source-system and drilling-logic neutral.
2. Source platforms remain authoritative; future Fabric/OSDU/SAP/PI bindings supply evidence rather than own the IQ.
3. Customer data is not used to train CEPIO models.
4. Readiness is an evidence-backed assessment at a point in time, not an unexplained persistent truth.
5. Customer-specific vocabulary belongs in profiles/mappings, not canonical ontology.
6. New IQ scenarios do not receive canonical classes simply because a test would become easier.
7. Safety-critical physical autonomy remains outside the pack.

## Next executable increments

After Rig Readiness qualification, the recommended sequence is:

### Reliability IQ

Compose failure history, condition evidence, open work, spares and campaign context to answer what is likely to fail and which intervention has the best expected operational value.

### Drilling Performance IQ

Separate recorded NPT from invisible lost time and normalized performance loss. Compare comparable sections/operations and explain parameter, connection, flat-time and procedural variance without treating correlation as enterprise fact.

### Commercial and Contract IQ

Continue an operational event into rate treatment, obligation/acceptance, claim entitlement, revenue-at-risk, margin and cash exposure.

### Well Control IQ

Expand the narrow readiness dimension into a dedicated assurance pack that reasons across test validity, configuration, defects, maintenance, upcoming operation and scoped authority.

These packs should compose over the same operating abstraction and replaceable evidence bindings rather than becoming independent applications.
