# ADR-0015: Maintenance deferral Skill runtime capability v0.3

## Status

Proposed

## Context

The CEPIO Labs `assess-maintenance-deferral` Skill remained statically BLOCKED after v0.2.3 because four logical capabilities had no exact runtime contract: `hasRisk`, `evaluate-maintenance-risk`, `maintenance-deferral-decision`, and `defer-work-order`.

The existing runtime also exposed `ApproveMaintenanceDeferral`, but its approval-oriented name was intentionally not treated as an exact semantic binding for the Skill's state-changing `defer-work-order` dependency.

## Decision

1. Add generic `core:hasRisk` from `Entity` to `Risk` so governed risk context can be linked without creating a maintenance-only core class.
2. Add `evaluateMaintenanceDeferralRisk`, which validates the Equipment→WorkOrder and Equipment→Risk graph and interprets governed risk evidence. It does not embed a universal engineering risk formula.
3. Add named Decision `maintenance-deferral-decision`, scoped to `WorkOrder`, with `DeferWorkOrder` as its allowed action.
4. Add `DeferWorkOrder` as the exact state-changing execution primitive. It is high-risk, human-approval governed, and executable only by maintenance/operations management roles.
5. Retain `ApproveMaintenanceDeferral` unchanged for compatibility; do not bind the Skill to it by name similarity.
6. Recommendation identities may recommend `DeferWorkOrder` but cannot execute it. Decision→Action causality continues through `decision_id` audit lineage.
7. Preserve the canonical failure graph `Equipment <- failureOfEquipment - FailureEvent - hasFailureMode -> FailureMode`; the Skill must not introduce a direct Equipment→FailureMode shortcut.

## Consequences

The maintenance-deferral Skill can become the second BOUND Skill only when its package explicitly declares the intermediate failure-event path, risk path, actor-visible evidence, function, Decision and action authority contract.

A READY preflight still does not mean a specific WorkOrder is safe to defer. Invocation-time evidence remains fail-closed, and the runtime risk function refuses to fabricate missing risk values or supported windows.

The generic core remains source-system neutral. Domain-specific RBI/APM or integrity models stay outside the generic function and feed governed Risk evidence into CEPIO.
