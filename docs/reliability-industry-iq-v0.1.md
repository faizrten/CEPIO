# Reliability Industry IQ v0.1

## Purpose

Reliability IQ is the cross-industrial CEPIO decision layer for turning governed equipment condition, failure, maintenance and risk evidence into deterministic reliability assessments and governed intervention recommendations.

It is deliberately not a new reliability ontology. It reuses the existing CEPIO industrial graph and existing governed maintenance actions.

## First executable operating question

> Given current governed equipment-condition evidence, active failure/risk context and maintenance work, is the asset reliability state acceptable; what evidence threatens continued service; and which governed maintenance intervention should be considered?

The runtime returns exactly one state:

- `RELIABLE`
- `DEGRADED`
- `INTERVENTION_REQUIRED`

No synthetic reliability score is required.

## Canonical graph

```text
Equipment
  |-- hasConditionObservation --> ConditionObservation
  |-- hasWorkOrder ------------> WorkOrder
  |-- hasRisk -----------------> Risk
  |
  <- failureOfEquipment -- FailureEvent -- hasFailureMode --> FailureMode
```

Reliability IQ consumes that graph. It does not create a parallel model for drilling, refinery, petrochemical or other asset-intensive domains.

A `DrillingEquipment` instance therefore uses the same reliability reasoning as any other `Equipment` subtype.

## Evidence rules

### Condition evidence

At least one `ConditionObservation` is required. Every supplied observation must:

- be linked to the assessed equipment through `hasConditionObservation`;
- have a normalized status;
- have a current validity horizon at assessment time;
- fail closed if it conflicts with another current observation for the same normalized `signalKey`.

Current normal evidence supports `RELIABLE`. Advisory/degraded evidence produces `DEGRADED`. Material/critical evidence produces `INTERVENTION_REQUIRED`.

### Failure evidence

Supplied `FailureEvent` evidence must be scoped to the equipment through `failureOfEquipment`. Active failures require `FailureMode` evidence. Closed historical failures remain part of the evidence bundle without being treated as current failure state.

### Maintenance evidence

Supplied `WorkOrder` evidence must be linked through `hasWorkOrder`. Active work is interpreted from its governed status and priority. Blocked, overdue, critical or emergency work can require intervention; completed work remains historical evidence.

### Risk evidence

Supplied `Risk` evidence must be linked through `hasRisk`. Active high/material/critical risk requires intervention. Closed or mitigated risk remains contextual evidence.

## Governed intervention boundary

Reliability IQ does not introduce new action primitives. It may recommend only existing CEPIO governed actions:

- `CreateInspection`
- `CreateWorkOrder`
- `EscalateRisk`

The existing named Decision remains:

`maintenance-intervention-recommendation`

An AI recommender may assess evidence and propose the Decision. It cannot execute the maintenance action. Existing human role/policy enforcement remains authoritative and every action remains audited.

If the evidence requires intervention but no existing action safely represents the required response, v0.1 returns no invented action and routes the case to human maintenance review.

## Reliability IQ vs Maintenance Deferral

These are intentionally separate capabilities.

**Reliability IQ:**

> Does current reliability evidence require an intervention, and why?

**Maintenance Deferral Skill:**

> Can an already-planned work order be deferred within governed risk constraints?

`REL-IQ-007` therefore reuses `cepio.skill.maintenance.assess-maintenance-deferral`; Reliability IQ does not clone it.

## Product boundary

- canonical ontology fork: prohibited;
- source systems remain authoritative;
- evidence bindings are replaceable;
- AI assessment is not automatically an enterprise fact;
- customer data is not used to train CEPIO;
- safety-critical physical autonomy is prohibited;
- drilling is an initial proving context, not the owner of reliability semantics.

## v0.1 qualification target

The implementation must demonstrate:

1. deterministic reliability classification;
2. current and correctly scoped condition evidence;
3. traceable failure-mode, work-order and risk evidence;
4. fail-closed behavior for stale, unscoped, malformed and conflicting evidence;
5. recommendation limited to existing governed actions;
6. AI recommendation separated from human execution authority;
7. reuse by `DrillingEquipment` without semantic extension;
8. no canonical ontology change;
9. no regression to the existing maintenance-deferral capability;
10. full CI, Quality Gate and CodeQL success.
