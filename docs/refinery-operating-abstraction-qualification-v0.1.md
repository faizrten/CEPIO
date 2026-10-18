# Refinery Operating Abstraction Qualification v0.1

## Purpose

Phase 7 moves refinery work from semantic completeness to executable operating-abstraction proof.

The qualification asks whether CEPIO can:

1. reconstruct cross-domain refinery context from one operating graph;
2. ground every operational answer in CEPIO runtime evidence;
3. preserve temporal/provenance requirements in the competency contract;
4. prevent an AI actor from bypassing action authority;
5. require human approval for a high-risk maintenance intervention;
6. execute one source-neutral external write exactly once;
7. verify the external result and record immutable workflow/audit evidence.

This is intentionally aligned to the CEPIO North Star:

> CEPIO is the canonical industrial semantic and operational contract; customer systems remain systems of record and Microsoft services provide the data, AI and hosting planes.

## Frozen operating questions

`generalization/competency/refinery-operating-abstraction-v0.1.yaml` freezes five operating questions:

| ID | Operating chain | Primary personas |
|---|---|---|
| ROA-001 | deviation -> envelope -> procedure -> permit/authority context | console operator, shift supervisor, field operator |
| ROA-002 | condition -> equipment -> production consequence -> work -> spare | reliability, maintenance, production assurance, finance |
| ROA-003 | crude characterization -> blend intent -> lot -> movement -> route | economist, scheduler, movements |
| ROA-004 | off-spec lot -> specification -> disposition -> affected movement | quality, scheduler, movements |
| ROA-005 | emissions + energy KPI -> limit/unit context -> corrective action context | energy, environmental, operations, finance |

The pack is separate from the historical refinery v0.1/v0.2 benchmarks. Those benchmarks remain frozen and unchanged.

## Runtime evidence qualification

`generalization/runtime/refinery-operating-abstraction-v0.1.yaml` materializes synthetic/source-neutral fixtures for all five questions.

The generic CEPIO runtime-coverage engine must prove for every question that:

- the required objects and relationships can be materialized;
- the expected cross-domain graph traversal resolves deterministically;
- property evidence resolves to the expected value;
- a supported answer cites only evidence produced by the current bundle;
- a fabricated evidence identifier is rejected fail-closed.

Target: **5/5 PASS and 100% runtime evidence coverage**.

## K-201 governed-action lighthouse

`scripts/run_refinery_operating_qualification.py` adds a second, stronger gate around the existing K-201 North Star scenario.

Synthetic sequence:

```text
K-201 high condition/risk
        -> CEPIO decision
        -> contextual policy evaluation
        -> human approval requirement
        -> CreateWorkOrder
        -> source-neutral external binding (synthetic_sap)
        -> external verification
        -> WorkflowOutcome
        -> immutable action/policy audit
```

The gate explicitly proves:

- direct AI-only `CreateWorkOrder` is denied;
- high-risk K-201 policy pauses the workflow for approval;
- an AI actor cannot approve its own governed intervention;
- an authorized maintenance manager can approve;
- the write is dispatched exactly once;
- verification is executed exactly once;
- replay remains idempotent;
- policy evidence is retained on the action audit;
- the workflow records a verified `WorkflowOutcome`.

## What this qualification does not claim

This phase uses synthetic/source-neutral fixtures and `FakeGovernedWriteAdapter` under a `synthetic_sap` binding.

It does **not** claim that SAP S/4HANA, AVEVA PI or any customer system has been qualified live.

The CEPIO v0.5 product release gate remains:

```text
PI anomaly
 -> CEPIO observation/state/provenance
 -> reliability reasoning + evidence/uncertainty
 -> Decision
 -> contextual policy
 -> human approval
 -> Kinetic workflow
 -> real SAP work order
 -> SAP read-back
 -> verification/reconciliation
 -> WorkflowOutcome
 -> audit
```

Phase 7 therefore proves that the **operating abstraction is ready for the live integration proof**. It is a prerequisite for the v0.5 gate, not a substitute for it.

## CI gates

The refinery CI lane now runs:

1. the historical frozen refinery baseline;
2. normalized refinery semantic capability benchmark;
3. refinery standards/persona challenge;
4. refinery operating-abstraction semantic qualification v0.1;
5. refinery operating-abstraction runtime qualification v0.1.

All generated refinery reports are uploaded with the refinery CI evidence artifact.
