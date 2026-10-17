# Refinery Standards & Persona Gap Triage v0.2

## Baseline

The refinery standards/persona expansion v0.2 deliberately raised the competency bar after the v0.1 refinery remediation.

Measured baseline:

- 12 competency questions;
- 0 PASS / 12 PARTIAL / 0 FAIL / 0 ERROR;
- 49.4% semantic-check coverage.

This is a healthy generalization signal: every new question can already be expressed partly through existing CEPIO semantics, while the benchmark exposes concentrated gaps in refinery/process-industry depth.

The established normalized v0.1.1 refinery benchmark now reaches 90.2% semantic-check coverage after the previously accepted CORE and DOMAIN remediation. The v0.2 pack therefore measures a new competency frontier rather than re-opening the previous gaps.

## Architectural triage

The 17 decisions are classified as:

| Disposition | Decisions | Meaning |
|---|---:|---|
| CORE | 5 | reusable industrial-common semantics |
| DOMAIN | 7 | source-neutral process-industry semantics |
| PROFILE | 0 | no refinery customer/site vocabulary accepted |
| MAPPING | 3 | external model/metric/architecture federation |
| REJECT | 2 | literal benchmark semantics should not enter canonical ontology |

## CORE candidates

1. **Alarm and control** — alarm, rationalization and control-loop semantics belong in industrial-common because they recur across automated industrial domains.
2. **Damage mechanism and RBI** — reusable reliability/integrity semantics, not refinery-only concepts.
3. **Electrical equipment** — electric motors and motor-control centers are common industrial asset types.
4. **Asset management** — criticality and lifecycle planning belong in the common asset layer.
5. **Production capacity** — a reusable operational-performance measurement that connects asset reliability to business consequence.

## DOMAIN candidates

1. **Crude/feed assay** — refinery/process feed characterization linked to material streams.
2. **Blending and material movements** — blend plans, movements and transfer routes across storage assets.
3. **Procedure automation** — continuous-process procedures, steps and executions.
4. **Abnormal situation** — a process-operation state beyond a generic alarm event.
5. **Integrity operating window** — process conditions tied to equipment degradation/integrity risk.
6. **Process variable** — semantic identity of the controlled/measured process quantity, distinct from individual measurements.
7. **Process topology** — a minimal source-neutral piping/connection semantic carrying process streams.

## MAPPING / integration decisions

- **PA-DIM device semantics** should federate into existing CEPIO Equipment, FunctionalLocation, Measurement and ConditionSignal identities rather than create a second process-device hierarchy.
- **Availability KPI** should use generic KPI/KPIObservation semantics, with formula and source terminology in the semantic-metric mapping layer.
- **NAMUR NOA monitoring/optimization channel** belongs in an integration binding / DigitalAsset representation because it is an architecture pattern, not refinery operational vocabulary.

## REJECT decisions

- `process:YieldModel` is rejected as canonical ontology. Executable yield models should be represented as versioned DigitalAssets/model-registry bindings; their inputs, outputs and business context remain semantic.
- a typed `ProcedureExecution -> WorkPermit` ontology predicate is rejected because existing `cepio:dependsOn` already composes procedures with permits, isolations, barriers and approvals.

The benchmark should be revised in its next frozen version to test those replacement patterns instead of rewarding class/predicate proliferation.

## Remediation sequence

Recommended implementation order:

1. **Procedure + alarm operations** — highest impact on operator/shift/control personas and ISA-106/IEC 62682 depth.
2. **Integrity + production assurance** — connects reliability, RBI, IOW, capacity and economic consequence.
3. **Blending + movements + planning** — fills the largest business-planning gap between refinery economics and physical execution.
4. **Instrumentation + engineering topology** — adds process variables and minimal topology while implementing PA-DIM/DEXPI/CFIHOS as federation mappings.
5. **Electrical + asset management** — rounds out common industrial asset competency without making refinery ontology the owner of electrical semantics.

Each semantic family should be remediated in a separate minimal PR. The frozen v0.2 challenge remains unchanged so improvements are measurable against an immutable baseline.
