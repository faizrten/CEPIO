# Refinery Procedure + Alarm Operations — v0.2

## Purpose

This slice implements the first remediation family from the refinery standards/persona v0.2 benchmark: continuous-process procedure execution and alarm/control-room semantics.

The design follows the accepted Generalization Lab triage. It strengthens reusable CEPIO modules without introducing a refinery-only ontology or customer-specific vocabulary.

## Standards grounding

The competency pressure comes from the existing CEPIO reference registry for:

- ISA-106 procedure automation / continuous-process operational procedures;
- IEC 62682 alarm management.

These standards are evidence and challenge references. CEPIO does not copy their full vocabularies.

## Process-industry semantics

`process_industry` adds:

- `process:OperatingProcedure` — controlled operational content, modeled as a `cepio:Document`;
- `process:ProcedureStep` — a procedure component, modeled as a reusable `cepio:Entity`;
- `process:ProcedureExecution` — an execution activity, modeled as `cepio:Activity`;
- `process:executesProcedure` — links an execution to the governing operating procedure;
- `process:AbnormalSituation` — time-varying process-operating state, modeled as `cepio:State`.

The module moves additively from `0.1.1` to `0.1.2`.

## Industrial-common alarm and control semantics

`industrial` adds:

- `industrial:Alarm` — industrial event representing an alarm occurrence/annunciation;
- `industrial:AlarmRationalization` — controlled rationalization evidence/content, modeled as `cepio:Document`;
- `industrial:ControlLoop` — reusable industrial functional asset;
- `industrial:alarmForState` — links an alarm to the generic `cepio:State` it represents;
- `industrial:rationalizesAlarm` — links rationalization content to the alarm it governs.

The module moves additively from `0.2.0` to `0.2.1`.

The common alarm model deliberately points to `cepio:State`, not `process:AbnormalSituation`. This preserves reuse in power, upstream, drilling, manufacturing and other automated domains while allowing process-industry abnormal situations to specialize the generic state.

## Work-control composition

Procedure execution does not gain special permit or isolation predicates.

The intended composition remains:

```text
ProcedureExecution
  executesProcedure -> OperatingProcedure
  dependsOn -> WorkPermit
  dependsOn -> EnergyIsolation
  dependsOn -> SafetyBarrier
  dependsOn -> WorkItem
  dependsOn -> other execution prerequisites
```

This keeps permits, isolations, barriers and approvals governed by their existing CEPIO modules and prevents process-domain coupling.

## Example operating graph

```text
OperatingProcedure
      ^
      | executesProcedure
ProcedureExecution
      |
      +-- dependsOn --> WorkPermit
      +-- dependsOn --> EnergyIsolation

AbnormalSituation -- represented by --> Alarm
                                      ^
                                      |
                         AlarmRationalization

ControlLoop -- dependsOn/impacts --> Equipment / State / Decision context
```

`industrial:alarmForState` provides the explicit Alarm -> State relation. Other graph relationships continue to use generic CEPIO predicates where they preserve the required meaning.

## Generalization guardrails

This slice intentionally does not add:

- `process:Alarm`, `process:AlarmRationalization` or `process:ControlLoop`;
- procedure-specific permit/isolation predicates;
- site-, refinery- or customer-specific procedure types;
- copied ISA-106 or IEC 62682 taxonomy trees;
- runtime automation behavior or external control-system side effects.

The frozen refinery v0.2 competency pack is unchanged so benchmark movement remains attributable to ontology remediation.

## Scope boundary

This PR covers only remediation family 1: **Procedure + Alarm Operations**.

The next accepted family remains **Integrity + Production Assurance**: damage mechanisms, RBI, integrity operating windows and production capacity semantics.
