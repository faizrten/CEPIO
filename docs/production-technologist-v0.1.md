# CEPIO Production Technologist v0.1

Status: **Experimental / executable depth slice**

## Purpose

Production Technology is modeled as the governed well-performance integration discipline between reservoir context, well/completion behavior, artificial lift, integrity limits, production operations and surface constraints.

The v0.1 persona mission is:

> Maintain safe, stable and economic well deliverability by continuously reconciling expected inflow and well performance with observed production, governed limits and surface constraints, then convert material deviations into evidence-backed recommendations.

The characteristic technical boundary is the producing/injecting well from the reservoir/sandface context to the surface choke, while consuming upstream reservoir/petrophysics context and downstream surface constraints.

CEPIO does **not** make the Production Technologist the owner of reservoir forecasts, completion execution design, control-room execution, facility process design or well-integrity exception authority.

## Why `production:` is a first-class CEPIO domain

Petrophysics is predominantly epistemic/interpretive. Production Technology is continuous, operational, constraint-heavy and action-adjacent. It needs a domain layer for well-performance assurance without turning CEPIO into a production historian, well-test repository, nodal simulator or artificial-lift application.

The module therefore owns only thin operating semantics:

- `production:ProductionAssuranceCase`
- `production:WellPerformanceAssessment`
- `production:DeliverabilityAssessment`
- `production:ProductionConstraintAssessment`
- `production:ArtificialLiftPerformanceAssessment`
- `production:WellIntegrityAssessment`
- `production:InterventionEffectivenessAssessment`
- `production:WellOperatingEnvelope`
- `production:WellOperatingLimit`
- `production:ProductionDeviation`

Technical payloads remain external and authoritative.

## Persona coverage

| Journey | Name | v0.1 runtime |
|---|---|---:|
| PROD-01 | Daily Well Surveillance & Exception Triage | yes |
| PROD-02 | Well Deliverability & Nodal Model Assurance | yes |
| PROD-03 | Production Optimization & Constraint Allocation | frozen |
| PROD-04 | Artificial Lift Performance & Optimization | frozen |
| PROD-05 | Well Integrity & Operating Envelope Assurance | frozen |
| PROD-06 | Well Underperformance Diagnosis | yes |
| PROD-07 | Production Enhancement & Intervention Opportunity | frozen |
| PROD-08 | New Well / Recompletion Start-up & Performance Acceptance | frozen |
| PROD-09 | WRFM Forecast & Production Plan Reconciliation | frozen |
| PROD-10 | Injection Well Performance & Conformance | frozen |

The first executable depth spine is deliberately:

```text
surveillance
    -> deliverability / model assurance
    -> competing-cause diagnosis
    -> discriminating evidence / recommendation
```

This establishes operating-state reasoning before CEPIO adds optimization or intervention workflows.

## Source-system boundary

The runtime capability contract is provider-neutral. Expected sources can include:

- historian / telemetry platforms;
- PRODML-compatible production exchange;
- OSDU or customer production services;
- WITSML or well-data services for completion/intervention context;
- well-test databases;
- nodal and network-model repositories such as PROSPER, PIPESIM or GAP;
- artificial-lift vendor/engineering systems;
- well-integrity / barrier-management systems;
- operations plans and surface-facility constraints.

No single platform is mandatory and CEPIO does not copy high-volume source payloads into canonical state.

### Standards context

- Energistics PRODML v2.3 was released in January 2025 and is the current PRODML version recommended by Energistics for new software development.
- ISO 16530-1:2017 remains the published well-integrity life-cycle governance standard as of the v0.1 design, with ISO/DIS 16530 under development as its successor.
- NORSOK D-010:2021+AC:2024 is the current consolidated NORSOK D-010 edition listed by Standard Norge.

These references inform capability and governance boundaries; CEPIO does not claim conformance merely by representing related concepts.

## Operating-envelope boundary

`production:WellOperatingEnvelope` is intentionally independent of `process:OperatingEnvelope`.

Both may eventually generalize to an industrial-common operating-envelope abstraction, but v0.1 does not force a well to inherit process-unit semantics. Generalization should be evidence-driven after cross-domain evaluation.

## Synthetic benchmark

Benchmark: `generalization/benchmarks/production-technologist-p118-v0.1.yaml`

All names and values are CEPIO-authored synthetic fixtures.

Focus well P-118 has:

- expected deliverability: 6,200 bopd;
- actual stable production: 4,750 bopd;
- deliverability gap: 1,450 bopd;
- water cut increased from 18% to 31%;
- lift gas at 1.4 MMscf/d versus a 2.0 MMscf/d model assumption;
- surface backpressure at 18 bar versus a 12 bar model assumption;
- current estimated drawdown of 52 bar under a governed 58 bar maximum;
- stale current-period downhole-pressure evidence.

The benchmark intentionally creates competing hypotheses:

1. elevated surface backpressure;
2. sub-optimal gas lift;
3. near-wellbore impairment;
4. reservoir depletion.

Each hypothesis includes supporting evidence, contradictory evidence where present, confidence, uncertainty and a falsification/discriminating-evidence test.

## Executable contracts

### PROD-01 — Surveillance and triage

CEPIO must distinguish a material technical exception from an evidence-quality problem.

Expected result:

```text
P-118 -> material_underperformance
P-121 -> data_quality_limited
P-115 -> normal
```

A data-limited well must not be converted into a fabricated root-cause diagnosis.

### PROD-02 — Deliverability assurance

CEPIO compares the authoritative external model result against current evidence and exposes changed assumptions.

Expected model-context drift:

- water cut;
- lift-gas rate;
- surface backpressure.

CEPIO explicitly does **not** recalculate nodal hydraulics. It recommends re-running/reconciling the authoritative engineering model.

### PROD-06 — Underperformance diagnosis

CEPIO ranks competing hypotheses while preserving the distinction:

```text
observation != diagnosis
```

Expected ranking:

```text
H-BACKPRESSURE
H-GASLIFT
H-NEARWELLBORE
H-DEPLETION
```

Every diagnosis must state what new observation, model sensitivity or governed test would materially weaken it.

## Authority

The `production_technologist` runtime role may read, reconcile, assess, diagnose and recommend.

It may not autonomously:

- change a live setpoint;
- start or stop a well;
- override a well operating envelope;
- approve an integrity deviation;
- approve a workover;
- execute an intervention;
- overwrite an external technical record.

Those boundaries are policy-gated and covered by fail-closed tests.

## Qualification gate

v0.1 is complete when:

```text
PROD-01  ANSWERED
PROD-02  ANSWERED
PROD-06  ANSWERED
Blocked  0
```

and:

- all Skill preflights are READY for `production_technologist`;
- an unauthorized control actor is blocked;
- source record/version identity is preserved;
- missing identity fails closed;
- CEPIO does not silently manufacture missing evidence;
- no live-control authority is granted.

## Next depth wave

Once the surveillance/deliverability/diagnosis spine is stable, expand in this order:

1. PROD-03 Production Optimization & Constraint Allocation;
2. PROD-04 Artificial Lift Performance & Optimization;
3. PROD-05 Well Integrity & Operating Envelope Assurance;
4. PROD-07 Production Enhancement & Intervention Opportunity;
5. PROD-08 Start-up / Performance Acceptance;
6. PROD-09 WRFM Plan Reconciliation;
7. PROD-10 Injection Performance & Conformance.

The key generalization test is whether these journeys continue to reuse Core Evidence/Hypothesis/Uncertainty, Kinetic Opportunity/Option/Decision and the narrow Production assurance layer without creating scenario-specific semantic silos.
