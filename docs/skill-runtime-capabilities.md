# Skill-facing runtime capability contracts

## Purpose

CEPIO Skills can declare procedural dependencies such as object types, relationships, functions, decisions and actions, but those declarations do not create runtime capability. A Skill is admitted only when its logical dependencies bind explicitly to CEPIO runtime contracts.

This document defines the first CEPIO runtime slice implemented for the `investigate-equipment-degradation` Skill experiment.

## Semantic capabilities

### `ConditionObservation`

`reliability:ConditionObservation` is reusable governed evidence about equipment condition. It is a `cepio:Measurement`.

`reliability:ConditionSignal` is a subtype of `ConditionObservation`, so sensor/signal-oriented condition evidence remains compatible without making all condition observations sensor-specific.

`reliability:hasConditionObservation` links `industrial:Equipment` to a `ConditionObservation`.

### `ProductionExposure`

`performance:ProductionExposure` is a `cepio:Measurement` representing prospective production quantity exposed during an asset-impact or intervention window.

It is intentionally distinct from `performance:ProductionLoss`. Exposure is quantity at risk while evaluating a condition or decision; loss may be estimated or realized after the fact.

## Function capability

The runtime registers:

```text
calculateProductionExposure(
  asset_id,
  hours,
  production_rate_per_hour
) -> float
```

The function validates that the target asset exists and returns `hours * production_rate_per_hour`. The production unit is supplied by the governed caller context; this function does not convert physical exposure into monetary impact.

## Named Decision capability

CEPIO now distinguishes a **DecisionDefinition** from a persisted **Decision** record.

```text
DecisionDefinition
  - name
  - allowed subject types
  - allowed actions

Decision
  - decision_type (optional for backward compatibility)
  - subject
  - problem
  - observations
  - recommendation
  - recommended / selected action
  - confidence / provenance metadata
```

The first registered definition is:

```text
maintenance-intervention-recommendation
  allowed subject type: Equipment
  allowed actions:
    - CreateWorkOrder
    - CreateInspection
    - EscalateRisk
```

Subtype validation uses the CEPIO TypeRegistry, so `Compressor` and `Pump` qualify as `Equipment` subjects. If a typed Decision names an unknown decision type, an invalid subject type or an action outside the definition, the runtime fails closed.

Existing Decision records without `decision_type` remain supported.

## Authority boundary

A named Decision capability is not executable authority. It constrains what recommendation record CEPIO accepts; Action execution still passes through the existing CEPIO policy, approval, precondition, idempotency and audit boundary.

This preserves the operating sequence:

```text
observe evidence
  -> calculate / evaluate
  -> persist bounded recommendation
  -> request governed action
  -> policy / approval / preconditions
  -> execute or reject
```

## Skill binding implication

The CEPIO Labs logical identifiers can now bind explicitly as follows:

| Skill logical dependency | CEPIO runtime contract |
|---|---|
| `ConditionObservation` | `https://cepio.org/ontology/reliability#ConditionObservation` |
| `ProductionExposure` | `https://cepio.org/ontology/performance#ProductionExposure` |
| `hasConditionObservation` | `https://cepio.org/ontology/reliability#hasConditionObservation` |
| `calculate-production-exposure` | `calculateProductionExposure` |
| `maintenance-intervention-recommendation` | `maintenance-intervention-recommendation` |

The binding remains explicit even where logical and runtime names happen to match.
