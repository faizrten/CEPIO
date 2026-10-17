# Skill-facing runtime capability contracts

## Purpose

CEPIO Skills can declare procedural dependencies such as object types, relationships, functions, decisions and actions, but those declarations do not create runtime capability. A Skill is admitted only when its logical dependencies bind explicitly to CEPIO runtime contracts and are reachable through the governed Operator/tool boundary.

This document defines the first CEPIO runtime slice implemented for the `investigate-equipment-degradation` Skill experiment.

## Semantic capabilities

### `ConditionObservation`

`reliability:ConditionObservation` is reusable governed evidence about equipment condition. It is a `cepio:Measurement`.

The pre-existing `reliability:ConditionSignal` contract remains unchanged for backward compatibility. `ConditionObservation` is a separate canonical evidence type for procedures that require an explicit governed observation abstraction rather than a source-specific signal model.

`reliability:hasConditionObservation` links `industrial:Equipment` to a `ConditionObservation`.

### Failure-history path

The Skill does not assume that `hasFailureMode` is directly attached to equipment. CEPIO's canonical reliability graph is:

```text
Equipment
  <- failureOfEquipment - FailureEvent
  - hasFailureMode -> FailureMode
```

The Operator relationship tool therefore supports governed outgoing and incoming traversal. This keeps the Skill aligned with existing relationship domain/range contracts instead of introducing a shortcut edge only for procedural convenience.

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

Function availability is not sufficient by itself. Calls through MCP/REST are evaluated against the actor's `functions` policy before the runtime invokes the registered function.

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

Named decision proposals are separately authorized by role. MCP and REST expose the same `cepio_save_decision` capability and derive `created_by` from authenticated actor identity rather than planner-supplied identity.

## Authority boundary

A named Decision capability is not executable authority. It constrains what recommendation record CEPIO accepts; Action execution still passes through the existing CEPIO policy, approval, precondition, idempotency and audit boundary.

A subsequent Action request can carry the originating `decision_id`, preserving the causal chain even when policy rejects execution.

This preserves the operating sequence:

```text
observe governed evidence
  -> calculate / evaluate
  -> persist bounded recommendation
  -> request governed action
  -> policy / approval / preconditions
  -> execute or reject
  -> retain Decision -> Action audit linkage
```

## Skill binding implication

The CEPIO Labs logical identifiers can now bind explicitly as follows:

| Skill logical dependency | CEPIO runtime contract |
|---|---|
| `ConditionObservation` | `https://cepio.org/ontology/reliability#ConditionObservation` |
| `ProductionExposure` | `https://cepio.org/ontology/performance#ProductionExposure` |
| `hasConditionObservation` | `https://cepio.org/ontology/reliability#hasConditionObservation` |
| `failureOfEquipment` | `https://cepio.org/ontology/reliability#failureOfEquipment` |
| `hasFailureMode` | `https://cepio.org/ontology/reliability#hasFailureMode` |
| `calculate-production-exposure` | `calculateProductionExposure` |
| `maintenance-intervention-recommendation` | `maintenance-intervention-recommendation` |
| `create-work-order` | `CreateWorkOrder` |

The binding remains explicit even where logical and runtime names happen to match.

## Admission lesson

Registry existence alone is not a sufficient Skill-admission criterion. A dependency must also be operationally reachable for the intended actor through the governed tool surface. v0.2.1 therefore treats semantic identity, graph reachability, policy authorization and causal auditability as parts of one runtime-binding contract.
