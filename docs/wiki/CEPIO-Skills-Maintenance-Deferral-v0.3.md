# CEPIO Skills — Maintenance Deferral v0.3

## Milestone

v0.3 makes `cepio.skill.maintenance.assess-maintenance-deferral` eligible to become the second statically BOUND and actor-aware READY Skill.

## Runtime contract

```text
Equipment
  |-- hasConditionObservation --> ConditionObservation
  |-- hasWorkOrder ------------> WorkOrder
  |-- hasRisk -----------------> Risk
  |
  <- failureOfEquipment -- FailureEvent -- hasFailureMode --> FailureMode
```

The Skill may call:

- `calculateProductionExposure`
- `evaluateMaintenanceDeferralRisk`

It may propose:

- `maintenance-deferral-decision` on a `WorkOrder`

It may recommend, but not directly execute:

- `DeferWorkOrder`

## Risk-evaluation boundary

`evaluateMaintenanceDeferralRisk` is an evidence interpreter, not a universal maintenance-risk model. The linked Risk evidence must contain the evaluated current risk score, risk score under the proposed deferral, maximum supported deferral window, and any hard constraint. Missing or malformed evidence fails closed.

This keeps RBI/APM, integrity-engineering and operator-specific quantitative methods in the appropriate external or domain layer while CEPIO governs identity, evidence, policy, Decision and Action lineage.

## Authority boundary

`DeferWorkOrder` is high-risk and requires a human role. The `ai_agent_recommender` identity can recommend it and propose the bounded Decision but cannot execute the WorkOrder state transition.

A maintenance manager or operations manager can execute the action through the governed runtime. The resulting audit retains the originating `decision_id`.

## Compatibility

The pre-existing `ApproveMaintenanceDeferral` action remains available for existing callers. It is not used as a shortcut binding for `defer-work-order`; v0.3 adds an exact `DeferWorkOrder` execution contract instead.
