# CEPIO Petrophysics — Formation Evaluation Assurance (PET-02) v0.1

## Purpose

PET-02 is the first executable persona journey for CEPIO Subsurface. It proves that CEPIO can turn technical subsurface records into an evidence-backed, uncertainty-aware and authority-governed formation-evaluation context without recreating OSDU, Azure Data Manager for Energy (ADME), Techlog, Petrel or another petrophysics system.

The reference persona is the **Petrophysicist / Formation Evaluation Specialist**.

The golden question is:

> **Show me the authoritative formation evaluation for Well A-17, Zone B. Explain why it changed, what evidence supports or contradicts it, what remains uncertain, and which current models, reserves cases, opportunities or decisions would be affected if the interpretation is wrong.**

## Product boundary

The design follows the Subsurface OSDU/ADME rule:

> **OSDU-first, extension-not-replication.**

OSDU/ADME remains the technical data plane. CEPIO adds assurance context, reasoning, uncertainty, authority, dependency and decision provenance.

```text
Wellbore DDMS / RAFS / interpretation systems
                 |
                 | external identity + version
                 v
             CEPIO Evidence
                 |
       +---------+----------+
       |                    |
  Assumptions          Contradiction
       |                    |
       +---------+----------+
                 v
      FormationEvaluationCase
                 |
       +---------+----------+
       |                    |
  Characteristics       Confidence
       |
  Uncertainty
       |
       v
 downstream dependency graph
       |
       +--> static model
       +--> reservoir model
       +--> reserves case
       +--> opportunity
       +--> decision
```

## Why FormationEvaluationCase is CEPIO-native

`FormationEvaluationCase` is not a replacement for a log set or a petrophysical interpretation payload. It is the operating context CEPIO needs to answer questions across technical systems and decision history.

A case binds:

- a well and interval context;
- external interpretation identity/version;
- evidence references;
- assumptions;
- petrophysical characteristics;
- uncertainty and confidence assessments;
- authority state;
- supersession lineage;
- downstream dependencies.

The technical curves, sample analyses and interpretation payloads remain in their authoritative systems.

## Semantic treatments

| Concept | Treatment | Authority |
|---|---|---|
| Well | BIND | OSDU owns technical well record; CEPIO provides enterprise handle. |
| Wellbore | REUSE | OSDU / Wellbore DDMS. |
| Well log | REUSE | OSDU / Wellbore DDMS. |
| Marker set | REUSE | OSDU / Wellbore DDMS. |
| Rock/fluid sample and analysis | REUSE | OSDU / RAFS DDMS. |
| Petrophysical interpretation record | EXTEND | External technical record remains authoritative; CEPIO adds reasoning sidecar. |
| FormationEvaluationCase | OWN | CEPIO assurance and decision context. |
| PetrophysicalCharacteristic | OWN | Domain subject for Core assessments. |
| Evidence / Assumption / Uncertainty / Confidence / InformationGain | OWN | Existing CEPIO Core epistemic model. |

## Domain characteristic pattern

Core defines **what an assessment is**. Petrophysics defines **what is being assessed**.

PET-02 introduces `subsurface:PetrophysicalCharacteristic` and first specializations:

```text
PetrophysicalCharacteristic
  +-- EffectivePorosityCharacteristic
  +-- WaterSaturationCharacteristic
  +-- PermeabilityCharacteristic
  +-- NetReservoirCharacteristic
  +-- NetPayCharacteristic
  +-- FluidContactCharacteristic
```

This intentionally avoids adding probability-distribution fields to Core.

Example:

```text
UA-SW-A17-ZB-v3
  rdf:type        core:UncertaintyAssessment
  core:assesses   A17-ZB-water-saturation-characteristic
```

The domain/profile may then carry range, ensemble, categorical or other quantitative representation as appropriate.

## Authority state

PET-02 distinguishes technical interpretation existence from organizational authority.

Formation evaluation state values are:

```text
Draft
UnderReview
Approved
Authoritative
Superseded
Rejected
```

An AI skill may compare, challenge, draft assessments and recommend. It must not declare an interpretation `Authoritative`, approve a reserves basis or overwrite an external technical record.

## First Skill pack

PET-02 intentionally starts with five bounded skills.

### Formation Evaluation Context

Resolves the well/interval, authoritative case, external source references and evidence inventory.

### Interpretation Delta

Explains what changed between current and superseded contexts, including findings, assumptions, methods and evidence.

### Assumption Trace

Traces Rw, Archie parameters, saturation model, cutoffs and transforms into assessed characteristics and downstream dependents.

### Core–Log Reconciliation

Surfaces material contradictions between log-derived interpretation and rock/fluid sample evidence.

### Downstream Impact

Traverses the dependency graph from the formation-evaluation case into current static models, reservoir model scenarios, reserves cases, opportunities and decisions.

All five skills are `recommend_only` in v0.1.

## Synthetic benchmark

The first benchmark is `CEPIO-SYNTH / R3 / A-17 / Zone B`.

It contains two formation-evaluation revisions:

```text
FE-A17-ZB-v2  -> Superseded
FE-A17-ZB-v3  -> Authoritative
```

v3 changes:

- `Rw`: 0.071 -> 0.064 ohm-m;
- Archie `m`: 2.00 -> 2.15;
- porosity cutoff: 0.10 -> 0.09;
- permeability transform: V4 -> V5;
- Sw: 0.34 -> 0.29;
- net pay: 11.2 -> 13.8 m;
- interpreted contact: -2418 -> -2423 m TVDSS.

The benchmark also includes deliberate contradiction:

```text
Current log-derived permeability = 112 mD
RCA core evidence                = 71 mD
```

CEPIO must not hide this inconsistency. It should lower or qualify confidence and trace which downstream artifacts may be affected.

## Downstream impact chain

The benchmark dependency chain is:

```text
FE-A17-ZB-v3
    |
    +--> SM18 static model
    |       |
    |       +--> RM21 reservoir model scenario
    |
    +--> RC26 reserves case
    |
    +--> OP-118 opportunity
             |
             +--> DEC-INFILL-R3-2026 decision
```

This is the first concrete proof of the CEPIO principle:

> **A changed technical belief must be traceable to the enterprise decisions that rely on it.**

## Acceptance contract

PET-02 v0.1 passes only when CEPIO can establish all of the following from the benchmark:

1. `FE-A17-ZB-v3` is the authoritative case.
2. `FE-A17-ZB-v2` is the immediately superseded context.
3. The material assumption and finding deltas are exposed.
4. Every external evidence item preserves source record and version identity.
5. `EV-CORE-RCA` is surfaced as contradictory evidence rather than silently averaged away.
6. water-saturation and fluid-contact uncertainty remain explicit.
7. the downstream impact reaches `SM18`, `RM21`, `RC26`, `OP-118` and `DEC-INFILL-R3-2026`.
8. AI authority fails closed at recommendation: it cannot declare the interpretation authoritative.

The executable fixtures and tests are:

- `generalization/personas/subsurface-petrophysics-v0.1.yaml`
- `generalization/competency/subsurface-petrophysics-pet02-v0.1.yaml`
- `generalization/benchmarks/subsurface-petrophysics-pet02-a17-zone-b.yaml`
- `tests/test_petrophysics_pet02_contract.py`

## Runtime binding

PET-02 resolves logical capabilities, not hardcoded endpoints:

```text
subsurface.well.master             -> ADME OSDU Core
subsurface.wellbore.master         -> ADME Wellbore DDMS
subsurface.wellbore.log            -> ADME Wellbore DDMS
subsurface.wellbore.marker         -> ADME Wellbore DDMS
subsurface.sample.analysis         -> ADME RAFS DDMS
subsurface.pressure.evidence       -> customer profile binding
subsurface.interpretation.petrophysics -> customer profile binding
```

The last two deliberately remain customer-profile bindings in v0.1 because CEPIO must not assume one vendor/tool or data route for formation-pressure and petrophysical interpretation products.

## What PET-02 does not do

PET-02 does not:

- calculate Archie saturation itself;
- run multimineral inversion;
- calculate NMR permeability;
- copy LAS/bulk log payloads into CEPIO;
- copy RAFS analysis payloads into CEPIO;
- replace Techlog, Petrel or other interpretation environments;
- approve an authoritative technical interpretation;
- approve reserves;
- make a well-investment decision.

Specialized engines perform technical computation. CEPIO governs the context, evidence, assumptions, reasoning, uncertainty, authority and consequences of those computations.

## Next increment

After PET-02 v0.1 is green, the next implementation increment should be **PET-02 runtime execution**, not a second journey. It should instantiate the benchmark into the CEPIO runtime, bind `ExternalRecordReference` objects to OSDU/ADME capabilities, execute the five Skill preflights, and produce one machine-verifiable answer object for the golden question.
