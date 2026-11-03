# Operational State Alignment v0.1 (M3) — read-only reference

**Status:** offline synthetic qualification candidate. Built upon merged M1
PR #323 and merged M2 PR #328; neither is a product-release or live-source claim.

## Objective

Make source-to-operational-state **consistency testable** without duplicating
CEPIO's ontology, temporal repository, binding fabric, agent runtime or
governed execution mechanism.

The M3 reference implements
`assess_operational_state_alignment(service, host_mapping, source_selections,
trusted_context, valid_at=..., evaluated_at=...)`.
It reuses M1 actor-scoped object inspection, M2 historical source checks,
CEPIO's existing PropertyRegistry, Binding Contract and the host-injected
`ExecutionContext`.

## Host-owned configuration

The host defines `HostStateAlignmentPlan` with a tenant, subject, canonical
**string** property IRI, mapping/version and an explicitly allowed value
vocabulary. The host also selects one **primary** and up to three
`corroborating` source bindings and their existing M2 record plans.

**Primary denotes the host's designated evidence lead, not proven
authoritativeness.** The input evidence is a strict normalized source record:

```text
organization_id
subject_id
observed_at
property_iri
state_value
mapping_id
mapping_version
```

This is an adapter-side normalized contract; source-specific field names,
conversions and crosswalks remain external. Unknown fields and unregistered
property IRIs fail closed. The module copies only the three M2 metadata fields
into the M2 evidence validation boundary. It captures each normalized source
observation during **the same single binding resolution**; it does not
double-read a source and risk contradictory versions between the two checks.

## Acceptance behavior

1. Validate host tenant, source count (1–4), uniqueness, primary role and
   source-plan scope before source I/O.
2. Require an IRI that exists in the existing canonical property registry and
   is a string property; no new status vocabulary is introduced into Core.
3. Require actor visibility of the subject and selected property before
   accessing any binding; M2 independently reauthorizes the historical object.
4. Require versioned read-only source bindings, matching source record kind,
   identity, source system, organization, subject, valid observation time and
   configured freshness window through M2.
5. Reject unrecognized mapping ID/version/property, unapproved state labels,
   mismatched historical snapshots and historical property-value type drift.
6. Treat any contradictory source values as `conflict_blocked`; a host-selected
   primary source cannot silently override conflicting evidence.
7. When all sources agree but disagree with the authorized historical state,
   return `historical_mismatch`.
8. When the sources agree with history but represent fewer than two distinct
   source systems, return `insufficient_independent_sources`.
9. Only agreeing, timely claims from **two independent source systems** whose
   value matches the authorized historical property produce
   `consistent_candidate`. This is still **not** qualified operational truth.

All outcomes carry `source_authenticity=not_attested`,
`state_authority=not_qualified` and `decision_eligible=false`. This
module does not update objects, add events, register new actions, execute a
Skill, persist a Decision or dispatch any source write.

## Why we do not call the result "live"

Source record/version consistency is not cryptographic source attestation.
Two bindings can be fabricated or ultimately share a non-independent upstream
origin. M2 now constrains historical CEPIO object selection by valid time and an
`evaluated_at` transaction-time cutoff, preventing later object corrections
from being used retroactively. However, the external record is resolved at
inspection time: it does not prove the source record was available to an
operator at the historical evaluation time.
A successful synthetic value comparison also does not validate sensor
calibration, engineering formulas, industrial safety envelopes, or the
domain-specific rule translating telemetry into operating state.

Those require real source identity and permissions, source-authenticated event
time and provenance, independent SME-approved mappings, bitemporal as-of
verification, operational constraints and source-side reconciliation.

## Verification

```bash
PYTHONPATH=src pytest -q tests/test_operational_state_alignment_v01.py
```

The synthetic test suite exercises consistency, explicit disagreement, stale
evidence, source/tenant/identity mismatch, IRI/property visibility, missing or
invalid mapping, non-independent corroboration and no Decision/Action
mutation. Full CI, static typing, CodeQL and deletion-aware coverage remain
mandatory; a green test subset does not qualify release advancement.

## Governance / deployment

- Generic source-neutral implementation only in CEPIO Core.
- Protected reliability/topology reasoning, private expert evidence and
  evaluation methods remain in CEPIO Labs.
- No new database schema or Azure/Foundry configuration, customer data,
  licensed parser, or paid model inference.
- The public API and hosted MCP surface are **unchanged**; this is a
  trusted-host-only reference, not a self-service tool.
- Existing v0.5 CONNECT and v1 scorecard authority remain unchanged.

**Next gate:** qualify evidence-to-state conversion under a real, authenticated
enterprise binding, including bitemporal availability and permitted use;
then expose a minimal actor-scoped workbench through existing CEPIO protocol
surfaces after security review. Close a real governed Action/verify/reconcile
loop only when the v0.5 CONNECT prerequisites are satisfied.
