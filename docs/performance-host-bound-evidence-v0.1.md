# Host-bound Performance Evidence Materialization v0.1

## What this changes

Adds a **read-only provider-neutral evidence materialization boundary** that
returns directly evaluable `PerformanceObservation` instances for the
existing Performance Service, Performance Industry IQ Decision bridge, and
headless executive preview.

It specifically closes the **caller-supplied value** gap identified in
Executive Preview v0.1 (#311) *for host-configured plans*. It does **not**
claim that a real provider source has been cryptographically authenticated,
that Fabric/SAP/PI is live, or that a customer KPI formula was actually
executed from external data.

## Security and authority

```text
Authenticated ExecutionContext (host owns tenant and actor)
                  ↓
HostEvidencePlan (host owns contract/subject/source record IDs)
                  ↓
Tenant check → pinned Performance Contract revision
                  ↓
Authorized CEPIO subject read
                  ↓
Explicit BindingRegistration (evidence / ready only)
                  ↓
EvidenceBinding.resolve_evidence(host-owned external ID)
                  ↓
Source-system + record-ID + version + kind + scope + formula-ref validation
                  ↓
Timestamp freshness and nonfinite-number validation
                  ↓
PerformanceObservation + immutable ExternalRecordReference stable key
                  ↓
Existing PerformanceIndustryIQService.reason / PerformanceService
                  ↓
Recommend-only governed Decision proposal
```

Clients can only select an **existing plan ID and evaluation time**.
They cannot submit evidence values, URLs, tenant IDs, source identifiers,
formula references, user identity or roles. Plan identities, source record IDs
and record-to-performance-node mappings are configured in the host, not
discovered by name or accepted from a request.

Fail-closed behavior:
- tenant mismatches are denied **before** source retrieval;
- the CEPIO subject must be read-authorized and match the configured type;
- binding manifest must be evidence-only and declare versioned identity;
- missing required focus evidence blocks the request;
- optional evidence may be absent but must remain **unknown**, never green/zero;
- source organization, subject, node, record identity/kind, record version,
  formula reference, and freshness must match;
- malformed, nonfinite or future values are rejected rather than normalized;
- binding registration status \`ready\` is **not** treated as live readiness.

A source payload's \`formula_ref\` is a **declared versioned convention**.
Matching that string does not attest external formula execution. Actual
customer-approved calculation qualification and trusted upstream
authentication belong in a further provider-specific integration gate.

## Public core vs tenant ownership

The core schema, resolution logic and validation are generic. Customer
formulas, source IDs, operating targets and KPI-to-source plans remain
tenant-controlled. This v0.1 ships no customer plan and no new live binding.

The sample in
`tests/test_performance_evidence_binding_v01.py`
uses fictional Rig 07 records and a fake read-only source adapter. The
source IDs/versions and values are purely test fixtures and are not
authoritative evidence of any physical rig, commercial arrangement or
safety status.

## Run focused verification

```bash
PYTHONPATH=src pytest -q tests/test_performance_evidence_binding_v01.py
```

Tests cover tenant and object authorization before reads, versioned identity,
missing records, optional commercial/HSE evidence, invalid source attributes,
stale/future evidence, formula-convention mismatch, wrong node, insufficient
binding declaration, and safe composition into the existing Industry IQ
Decision proposal.

## Deliberately deferred

- Production source-side signatures, identity attestation, freshness monitoring,
  token/managed-identity lifecycle and binding registration readiness.
- A real customer-approved NPT formula executed over live verified time intervals.
- HTTP REST or MCP registration for this path. The host must first register a
  genuine evidence adapter and a tenant-scoped \`HostEvidencePlan\`.
- Live Copilot/Teams and Industry IQ Studio acceptance.
- Persisting or executing any Decision, workflow or Action.

The next acceptance gate should be the **Fabric-backed Rig 07 read-only
source proof**, with negative tenant controls and replayable revisions, then
a provenance-complete executive preview composed from this boundary.
