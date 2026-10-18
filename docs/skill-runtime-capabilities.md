# Skill-facing runtime capability contracts

## Purpose

CEPIO Skills can declare procedural dependencies such as object types, relationships, functions, decisions and actions, but those declarations do not create runtime capability. A Skill is admitted only when its logical dependencies bind explicitly to CEPIO runtime contracts and are reachable through the governed Operator/tool boundary.

This document defines the reusable CEPIO runtime contracts proven by the Skills experiments.

## Semantic capabilities

### `ConditionObservation`

`reliability:ConditionObservation` is reusable governed evidence about equipment condition. It is a `cepio:Measurement`.

The pre-existing `reliability:ConditionSignal` contract remains unchanged for backward compatibility. `ConditionObservation` is a separate canonical evidence type for procedures that require an explicit governed observation abstraction rather than a source-specific signal model.

`reliability:hasConditionObservation` links `industrial:Equipment` to a `ConditionObservation`.

### Failure-history path

Skills do not assume that `hasFailureMode` is directly attached to equipment. CEPIO's canonical reliability graph is:

```text
Equipment
  <- failureOfEquipment - FailureEvent
  - hasFailureMode -> FailureMode
```

The Operator relationship tool therefore supports governed outgoing and incoming traversal. This keeps Skills aligned with existing relationship domain/range contracts instead of introducing shortcut edges only for procedural convenience.

### `ProductionExposure`

`performance:ProductionExposure` is a `cepio:Measurement` representing prospective production quantity exposed during an asset-impact or intervention window.

It is intentionally distinct from `performance:ProductionLoss`. Exposure is quantity at risk while evaluating a condition or decision; loss may be estimated or realized after the fact.

### `hasRisk`

`core:hasRisk` is a generic, reusable relationship from a CEPIO `Entity` to a CEPIO `Risk`. It exists to connect governed risk context to the entity whose decision is being evaluated without forcing a maintenance-specific risk class into the core ontology.

For maintenance deferral, the Skill binds `Equipment -> hasRisk -> Risk`. Domain-specific risk models remain external, profile-specific, or represented by specialized `Risk` subtypes.

## Function capabilities

The runtime registers:

```text
calculateProductionExposure(
  asset_id,
  hours,
  production_rate_per_hour
) -> float
```

The function validates that the target asset exists and returns `hours * production_rate_per_hour`. The production unit is supplied by the governed caller context; this function does not convert physical exposure into monetary impact.

For maintenance deferral the runtime also registers:

```text
evaluateMaintenanceDeferralRisk(
  equipment_id,
  work_order_id,
  risk_id,
  proposed_deferral_hours
) -> MaintenanceDeferralRiskAssessment
```

This function deliberately does **not** invent an engineering risk model. It validates that the WorkOrder and Risk are actually linked to the Equipment, then interprets governed values already present on the linked Risk evidence: current risk score, evaluated risk under deferral, maximum supported deferral hours, and any hard constraint. Missing or malformed risk evidence fails closed.

Quantitative risk estimation may come from RBI/APM, operator engineering assessment, integrity models, or another governed source. CEPIO performs identity, evidence and decision governance around that result rather than pretending one generic formula is valid for every industrial domain.

Function availability is not sufficient by itself. Calls through MCP/REST are evaluated against the actor's `functions` policy before the runtime invokes the registered function.

## Named Decision capability

CEPIO distinguishes a **DecisionDefinition** from a persisted **Decision** record.

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

Registered definitions used by Skills include:

```text
maintenance-intervention-recommendation
  allowed subject type: Equipment
  allowed actions:
    - CreateWorkOrder
    - CreateInspection
    - EscalateRisk

maintenance-deferral-decision
  allowed subject type: WorkOrder
  allowed actions:
    - DeferWorkOrder
```

The deferral decision is WorkOrder-scoped because the governed question is whether a specific maintenance obligation may move in time. The Equipment remains the source of condition, failure, risk and consequence evidence.

Subtype validation uses the CEPIO TypeRegistry. If a typed Decision names an unknown decision type, an invalid subject type or an action outside the definition, the runtime fails closed.

Existing Decision records without `decision_type` remain supported.

Named decision proposals are separately authorized by role. MCP and REST expose the same `cepio_save_decision` capability and derive `created_by` from authenticated actor identity rather than planner-supplied identity.

## Authority boundary

A named Decision capability is not executable authority. It constrains what recommendation record CEPIO accepts; Action execution still passes through CEPIO policy, approval, precondition, idempotency and audit controls.

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

### Approval is not the same semantic as deferral

The pre-existing `ApproveMaintenanceDeferral` action is retained for compatibility. The maintenance-deferral Skill does not bind its logical `defer-work-order` capability to that name by convenience.

v0.3 adds an explicit `DeferWorkOrder` action. It represents the state-changing WorkOrder transition and remains high-risk and human-approval governed. This gives the Skill an exact execution capability while preserving the legacy action surface.

The recommendation actor may recommend `DeferWorkOrder` but cannot execute it. Human maintenance/operations management roles may execute it through the governed action boundary. Decision-to-Action `decision_id` linkage remains auditable.

## Skill binding implication

Explicit logical-to-runtime bindings now include:

| Skill logical dependency | CEPIO runtime contract |
|---|---|
| `ConditionObservation` | `https://cepio.org/ontology/reliability#ConditionObservation` |
| `ProductionExposure` | `https://cepio.org/ontology/performance#ProductionExposure` |
| `Risk` | `https://cepio.org/ontology/core#Risk` |
| `hasConditionObservation` | `https://cepio.org/ontology/reliability#hasConditionObservation` |
| `failureOfEquipment` | `https://cepio.org/ontology/reliability#failureOfEquipment` |
| `hasFailureMode` | `https://cepio.org/ontology/reliability#hasFailureMode` |
| `hasRisk` | `https://cepio.org/ontology/core#hasRisk` |
| `calculate-production-exposure` | `calculateProductionExposure` |
| `evaluate-maintenance-risk` | `evaluateMaintenanceDeferralRisk` |
| `maintenance-intervention-recommendation` | `maintenance-intervention-recommendation` |
| `maintenance-deferral-decision` | `maintenance-deferral-decision` |
| `create-work-order` | `CreateWorkOrder` |
| `defer-work-order` | `DeferWorkOrder` |

The binding remains explicit even where logical and runtime names happen to match.

## Admission lesson

Registry existence alone is not a sufficient Skill-admission criterion. A dependency must also be operationally reachable for the intended actor through the governed tool surface. Skill admission therefore treats semantic identity, graph reachability, evidence visibility, policy authorization, least-privilege authority alignment and causal auditability as parts of one runtime-binding contract.
