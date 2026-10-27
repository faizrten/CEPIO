# Rig 07 Drilling Contractor Performance Activation v0.1

## Purpose

This is the first reproducible **synthetic activation** of the existing Drilling
Contractor Industry Performance Pack. It is a scenario acceptance proof, not a
production customer onboarding, not a real contractual estimate, and not a live
Copilot/Teams/Industry IQ Studio application.

Run from the repository root (no Azure, Fabric, SAP, historian, or paid model required):

```bash
PYTHONPATH=src python scripts/drilling_performance_activation_v01.py
PYTHONPATH=src pytest -q tests/test_drilling_performance_activation_v01.py
```

## Capability and data flow

```text
CEPIO Drilling Contractor reference PerformanceContract @0.1.0
   -> synthetic-rigco organization PerformanceContractOverlayV2
   -> in-memory versioned registry (active, pinned references)
   -> resolved effective contract + source revision hashes
   -> trusted, registered and typed Business Logic functions
   -> evidence-backed performance observations
   -> PerformanceService / deterministic PerformanceRuntime
   -> KPI / KR / guardrail status and provenance
   -> recommend-only, policy-required investigation candidate
```

The implementation reuses CEPIO's qualified contract registry, resolver, Business
Logic materializer, runtime, and headless Performance Service. There is no new
parallel KPI engine, alternate workflow runtime, or integration infrastructure.

## Synthetic policy and dataset

**All values are fictional.** They illustrate contract specialization and
deterministic evaluation, not a customer's definitions.

| Concept | Approved *synthetic* definition/condition | Fixture evidence |
|---|---|---|
| NPT ratio | Classified equipment NPT hours / eligible hours; KPI <= 8% | 12h / 120h = 10% |
| Rig 07 NPT key result | Decrease from a 10% baseline by 25%, i.e. <= 7.5% | Same NPT ledger and clock |
| Operational uptime | (Scheduled - attributable downtime) / scheduled; >= 95% | (120h - 12h) / 120h = 90% |
| Revenue leakage | **Contract-confirmed** nonbillable hours × approved hourly rate; <= $0 | 8h × $4,000 = $32,000 gross synthetic exposure |
| Serious safety events | Synthetic zero-incident guardrail, **not** a site safety limit | 0 events on an explicitly named synthetic register |
| Well-control barrier failures | Synthetic zero-incident guardrail, **not** a site safety limit | 0 verified events on a separate synthetic register |

For this fixture, a synthetic organization role replaces inherited generic Rig
Manager accountability for operational uptime. The reference graph and its other
reference personas remain intact. The synthetic policy is **never published into**
the industry-reference Performance Pack.

The financial number is *not* EBITDA loss, booked revenue loss, free cash flow,
or a prediction. It is only a multiplication supported by two designated,
fictional commercial inputs. CEPIO must not invent the number if these inputs
are unavailable. Likewise, no direct root cause, safety limit, or intervention
approval is inferred from an NPT ratio.

## Expected result

The NPT KPI, uptime KPI and NPT KR are off track on the synthetic facts.
Missing measured downstream economics remain unknown or only structurally at
risk; graph edges do not quantify causation. Explicit zero-event evidence is
required before guardrails can show on track.

The organization-specific NPT deviation emits one workflow **candidate**:
`drilling-rig07-reliability-investigation`.
The candidate is `recommend_only` and `policy_required=true`.
This script **never starts a workflow**, authorizes a side effect, sends a Teams
message, reads live external systems, or changes customer data.

## Acceptance and negative tests

- Pinned reference-plus-organization resolution, immutable reference semantics,
  field-level specialization and accountability rebinding.
- Evidence and formula-definition hash lineage.
- NPT/KR/uptime correctness from explicitly named synthetic observations.
- Missing financial evidence stays `unknown`; no projected $ value.
- Missing HSE/well-control evidence stays `unknown`; not green by default.
- Stale formula inputs, invalid denominators and cross-tenant formula execution
  fail closed.
- Determinism under identical evaluation inputs.
- Recommend-only workflow boundary remains intact.

## Explicitly not completed in P1-A/P1-B synthetic acceptance

- Connection to actual Rig 07 data, customer-approved time taxonomy, contractual
  dayrate or finance data.
- PostgreSQL activation persistence or organization administration UI.
- Quantitative driver attribution, root-cause confidence or EBITDA modelling.
- Executing a policy-approved maintenance action.
- Production Copilot/Teams entry point or Studio rendering.

These are later acceptance steps. The key purpose here is to prove CEPIO Core
can **operationalize** a customer-specialized performance reference using
evidence and governance without compromising tenant boundaries.
