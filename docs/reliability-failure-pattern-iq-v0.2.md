# Reliability IQ v0.2 — Failure Pattern & Recurrence IQ

## Purpose

REL-IQ-002 moves CEPIO Reliability IQ from single-asset intervention assessment to population-level failure-pattern reasoning.

The executable question is:

> Which equipment and failure modes are recurring beyond expected behavior, and what common causal evidence should change reliability strategy?

This capability remains cross-industrial. Drilling equipment is a proving context, not the owner of the reliability semantics.

## Boundary

REL-IQ-002 reuses existing canonical CEPIO semantics only:

- `Equipment`
- `FailureEvent`
- `FailureMode`
- `failureOfEquipment`
- `hasFailureMode`
- `startTime`
- `cause`

No new canonical reliability class, relationship, API operation or vendor schema is introduced.

The recurrence thresholds are explicit governed assessment inputs. They are not universal facts encoded in CEPIO Core or the reliability ontology.

## Result states

The assessment returns one of three states:

- `WITHIN_EXPECTATION` — no supplied failure pattern exceeds the configured recurrence expectations in the requested analysis window.
- `LOCAL_RECURRENCE` — at least one equipment/failure-mode pair, or a failure mode within a single-equipment population, exceeds governed expectation but does not satisfy the systemic cross-equipment gate.
- `SYSTEMIC_RECURRENCE` — a failure mode exceeds the population recurrence expectation and appears across at least the configured minimum number of distinct equipment items.

The corresponding strategy responses are `MONITOR`, `LOCAL_ENGINEERING_REVIEW` and `SYSTEMIC_RELIABILITY_REVIEW`.

## Evidence contract

Each supplied `FailureEvent` must:

1. be a governed `FailureEvent`;
2. carry a timezone-aware `startTime` inside the requested analysis window;
3. resolve through `failureOfEquipment` to exactly one `Equipment`;
4. resolve through `hasFailureMode` to exactly one `FailureMode`.

Duplicate failure-event identifiers are rejected so repeated input cannot manufacture recurrence.

A `cause` is optional. When present it must be a normalized string. CEPIO may surface a cause only when the same recorded cause is supported by at least the configured minimum number of events for a recurring failure mode.

Critically:

> repeated recorded cause is **common causal evidence**, not automatically proven root cause.

The output preserves the supporting failure-event IDs and equipment IDs so the human reliability engineer can inspect the evidence chain.

## REL-IQ-002 vs REL-IQ-005

REL-IQ-002 is deliberately not a bad-actor ranker.

```text
REL-IQ-002
Failure-event recurrence
→ repeated mode
→ common causal evidence
→ local/systemic reliability review

REL-IQ-005 (future)
Failure recurrence
+ operating/service exposure
+ maintenance exposure
+ normalized duty/context
→ persistent bad-actor ranking
```

This prevents an asset with more operating hours or more severe duty from being labeled a bad actor simply because it has more recorded failures.

## Agentic boundary

REL-IQ-002 performs deterministic assessment and recommendation only. It does not create a new maintenance action and it does not directly alter maintenance strategy, inspection programs, design, operating limits or physical equipment.

A systemic result routes evidence to human reliability-strategy review. Any later governed action remains subject to CEPIO Decision, policy, authority, approval and audit controls.

## North-star alignment

The pack is thick in industrial reasoning and thin in infrastructure:

```text
Authoritative failure history
        ↓
replaceable binding
        ↓
Equipment / FailureEvent / FailureMode evidence
        ↓
REL-IQ-002 recurrence assessment
        ↓
common causal evidence + strategy response
        ↓
human reliability review
```

Source systems remain authoritative, customer data is not used to train CEPIO, and customer-specific recurrence thresholds belong in deployment/profile configuration rather than customer ontology forks.
