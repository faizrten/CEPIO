# Operational State & Evidence Inspection v0.1 (M2 reference)

**Status:** additive offline, host-scoped reference; not product-release qualification.

## Purpose

Activate the operational ontology incrementally on top of M1 without adding
another schema, graph backend, agent engine, data fabric, source adapter or
production dependency.

This is a small **read-only** reference that composes existing:

- CEPIO `ContextEnvelope` and the M1 Operational Object Inspection;
- actor-scoped `CEPIOApplicationService.read_object` and Role/Policy Engine;
- `ContractAwareCEPIORuntime.get_object_valid_at` (existing temporal repository);
- `PlatformBindingManifest`, `BindingRegistration`,
  `EvidenceBinding` and `ExternalRecordReference`.

## Contract

`inspect_operational_state(..., plan, trusted_context, valid_at, evaluated_at)`

1. Requires timezone-aware times and valid-time no later than evaluation time.
2. Checks host tenant against an **explicit host-owned plan**, binding manifest /
   capability / ready status, evidence-only interface and versioned source identity.
3. Authorizes the subject **before accessing the source**. M1 also applies
   actor/property/relationship filtering to first-hop objects.
4. Reads a historical object by **valid time**, constrained to transactions recorded no later than `evaluated_at` through CEPIO's existing bitemporal repository.
   The historical object is reauthorized and property-filtered separately so an
   earlier broader sharing scope never bypasses current actor restrictions.
5. Resolves only the plan-pinned source record, validates source-system / kind /
   ID / nonempty version, checks normalized observation metadata
   (`organization_id`, `subject_id`, `observed_at`), and requires the
   observation time to precede the requested valid time and fall within the
   host-configured freshness window.
6. Returns the scoped `OperationalObjectInspection`, authorized historical
   subject and small versioned observation receipt. Source evidence *values*
   and external provider transport payloads are **not copied** into the result.

## Critical non-claims

A matching, versioned source record is **reference consistency**. It is not:

- cryptographic proof that the record originated from a trusted provider;
- proof that its measurement actually corresponds to a CEPIO state property;
- an authorized, live operational snapshot or certified source freshness;
- historical availability of the external source record (the source is resolved now);
- a production multi-tenant permission boundary, source-use grant or
  authorization to issue an external Action.

The response therefore explicitly says `authenticity=not_attested` and
`source_to_state_alignment=not_proven`. Later work must bind a validated
measurement/property mapping, source event-time/transaction-time semantics,
source-use authorization and, where appropriate, source attestations. No
unqualified status may be promoted to trusted operational state by an agent.

## Tests

```bash
PYTHONPATH=src pytest -q tests/test_operational_state_inspection_v01.py
```

The synthetic binding proves rejection of wrong tenant, denied subject/history,
invalid record identity/version/kind/source, malformed metadata, missing source,
stale/future/unzoned timestamps, incompatible manifests and unavailable temporal
history. CI must also confirm Core global coverage and existing contract checks.

## Roadmap and dependencies

Builds on **merged M1 PR #323**. M2 must independently complete its own governed
review and checks before integration. This work does
not advance the CEPIO v0.5 CONNECT release or v1 scorecard.

Subsequent increments: qualified source-value-to-state mapping with immutable
provenance and conflict reconciliation; persistence-backed state projections
over the chosen repository; authenticated REST/MCP consumption; actual PI/SAP
plus a third-source K-201 Decision -> approved Action -> verified Outcome.

No Azure deployment, new PostgreSQL schema, paid inference or customer data
is introduced by this reference. Protected Industry IQ reasoning remains in Labs.
