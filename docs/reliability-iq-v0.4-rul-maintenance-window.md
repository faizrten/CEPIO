# Reliability IQ v0.4 — Remaining Useful Life & Maintenance Window IQ

## Purpose

REL-IQ-004 connects governed remaining-useful-life evidence to planned maintenance timing without turning a model estimate into autonomous maintenance authority.

The executable question is:

> What governed remaining-useful-life estimate exists for critical equipment, how current and uncertain is it, and does a planned maintenance window complete before the conservative life horizon?

The capability is cross-industrial. The same contract applies to generic `Equipment` and derived domain equipment such as drilling equipment.

## Reused semantics

REL-IQ-004 introduces no new canonical ontology or public API contract. It reuses:

- `Equipment`
- `RemainingUsefulLifeEstimate`
- `estimatesLifeOf`
- `WorkOrder`
- `hasWorkOrder`
- `remainingUsefulLife`
- `confidence`
- `unitSymbol`
- `validFrom`
- `validTo`
- `scheduledStart`
- `scheduledEnd`

The canonical model already distinguishes a remaining-life **estimate** from observed equipment state. REL-IQ-004 therefore does not need a reliability-specific prediction class or a customer-specific schema.

## Uncertainty boundary

CEPIO's accepted ADR-008 establishes generic Core semantics for evidence, claims, assessments and uncertainty, while deliberately avoiding P10/P50/P90-specific fields and numerical-solver behavior.

That implementation branch currently predates the active Reliability IQ stack. REL-IQ-004 therefore does not create a competing ontology and does not merge the old branch implicitly.

For v0.4 the runtime function uses:

- canonical central `remainingUsefulLife` from the governed `RemainingUsefulLifeEstimate`;
- a governed lower RUL bound supplied through the pack contract;
- a governed upper RUL bound supplied through the pack contract;
- canonical `confidence` carried separately.

The contract enforces:

```text
0 < lower RUL <= central RUL <= upper RUL
0 <= confidence <= 1
```

Confidence is explicitly **not** treated as the uncertainty interval.

Once the accepted Core uncertainty implementation is rebased into the current runtime stack, the lower/upper contract can bind to `UncertaintyAssessment` without changing REL-IQ-004's operating logic.

## Estimate qualification

A supplied `RemainingUsefulLifeEstimate` must:

1. be a governed `RemainingUsefulLifeEstimate`;
2. resolve through `estimatesLifeOf` to exactly the assessed `Equipment`;
3. carry positive numeric `remainingUsefulLife`;
4. carry an expected engineering `unitSymbol`;
5. carry numeric `confidence` in `[0, 1]`;
6. carry timezone-aware `validFrom` and `validTo`;
7. be current at assessment time.

Expired, future-valid, malformed or ambiguous evidence fails closed.

The estimate state is:

- `CURRENT`
- `EXPIRING_SOON`

`EXPIRING_SOON` is controlled by an explicit assessment/profile warning horizon. It does not imply failure; it means the inference should be refreshed before further reliance.

## Life horizons

REL-IQ-004 derives three decision horizons from the assessment time:

```text
assessment time
   + lower RUL   -> conservative horizon
   + central RUL -> central horizon
   + upper RUL   -> optimistic horizon
```

The **conservative horizon** is used for maintenance-window compatibility. This is intentionally more cautious than using the central estimate as the execution boundary.

## Maintenance-window qualification

Candidate maintenance windows are existing `WorkOrder` schedule evidence.

Every supplied work order must:

1. be a governed `WorkOrder`;
2. be linked to the assessed equipment by `hasWorkOrder`;
3. carry timezone-aware `scheduledStart` and `scheduledEnd`;
4. have `scheduledEnd > scheduledStart`;
5. not already have started at assessment time.

Duplicate work-order IDs fail closed. Two different work orders with the exact same schedule interval are rejected as ambiguous duplicate schedule evidence.

Source maintenance systems remain authoritative for the schedule. CEPIO evaluates compatibility; it does not become the maintenance scheduler.

## Window compatibility

For every qualified window CEPIO calculates:

```text
completion offset = scheduledEnd - assessment time
conservative margin = lower RUL - completion offset
```

The window is classified as:

- `WINDOW_SAFE` — completion occurs before the conservative horizon with at least the configured minimum margin;
- `WINDOW_MARGIN_LOW` — completion occurs before the conservative horizon but with less than the configured margin;
- `WINDOW_AFTER_CONSERVATIVE_HORIZON` — completion occurs after the conservative horizon;
- `NO_QUALIFIED_WINDOW` — no candidate window was supplied.

When several candidate windows exist, REL-IQ-004 selects the best qualified compatibility state and then the earliest completion inside that state. It does not automatically reschedule any work.

## Review disposition

Window evidence maps to an advisory review disposition:

- `WINDOW_SAFE` -> `PLAN_MAINTENANCE_REVIEW`
- `WINDOW_MARGIN_LOW` -> `ACCELERATE_MAINTENANCE_REVIEW`
- `WINDOW_AFTER_CONSERVATIVE_HORIZON` -> `RISK_REVIEW`
- `NO_QUALIFIED_WINDOW` -> `MONITOR` when the conservative horizon lies beyond the configured planning horizon, otherwise `ACCELERATE_MAINTENANCE_REVIEW`

These are not actions.

REL-IQ-004 does **not**:

- create or reschedule a work order;
- approve maintenance deferral;
- revise an operating plan;
- change equipment operating limits;
- stop or start physical equipment;
- bypass REL-IQ-001, Decision, authority, approval or audit controls.

## Relationship to other Reliability IQ capabilities

```text
REL-IQ-003
Condition Monitoring
"What is deteriorating?"
        ↓
REL-IQ-004
RUL + Maintenance Window
"How much governed life remains and does the plan fit?"
        ↓
REL-IQ-001
Asset Intervention
"What intervention should be considered in full context?"
        ↓
Decision / policy / authority / approval
        ↓
Governed action
```

REL-IQ-002 remains orthogonal population-level recurrence reasoning:

```text
REL-IQ-002
Failure Pattern & Recurrence
"Is this isolated or systemic?"
```

## North-star alignment

```text
Authoritative condition / predictive-maintenance source
                      ↓
replaceable binding
                      ↓
RemainingUsefulLifeEstimate
+ governed uncertainty interval
                      ↓
REL-IQ-004
life horizons + schedule compatibility
                      ↓
review disposition + cited evidence
                      ↓
REL-IQ-001 / human reliability workflow
```

This keeps CEPIO thin in infrastructure and thick in industrial reasoning. Source systems remain authoritative, customer data is not used to train CEPIO, and customer-specific model thresholds or planning policies remain profile/assessment configuration rather than ontology forks.
