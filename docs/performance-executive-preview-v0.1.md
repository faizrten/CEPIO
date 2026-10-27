# Headless Executive Performance Preview v0.1

This is a **read-only, opt-in experimental** composition over the already-qualified
Performance Service and Performance Industry IQ service. It does not replace the
existing Enterprise Performance Graph, Industry IQ packs, decisions or workflows.

## Why

The Rig 07 synthetic performance acceptance (PR #309) evaluated individual
KPIs/KRs and a recommend-only workflow candidate. This increment presents them
together to an authenticated executive consumer:

- contract identity and immutable source-revision hashes;
- focus asset and deviation-specific Decision proposal;
- KPIs, metrics, objectives, KRs and safety guardrails, with observable status;
- reference/organization role accountabilities (not individual appraisals);
- evidence references, explicit missing-data and influence/structural risk flags;
- optional **observed currency metric**, only if explicitly selected and supported;
- policy-required workflow candidates, with no execution authority.

## Service composition

```text
Caller (Copilot / Teams / Studio adapter)
   -> authenticated ExecutionContext from host, NOT request body
   -> ExecutivePerformanceService.preview(...)
       -> existing PerformanceIndustryIQService.reason(...)
           -> tenant check; authorized CEPIO object read
           -> pinned Performance Contract
           -> evidence-backed deviation
           -> existing DecisionProposal (no persistence)
       -> existing PerformanceService.evaluate(...)
       -> typed, read-only ExecutivePerformancePackage
```

The executive service never registers formulas, performs new calculations,
promotes unverifiable claims or writes a Decision.

## REST experimental preview

The opt-in feature flag is disabled by default:

```bash
CEPIO_ENABLE_EXPERIMENTAL_PERFORMANCE_EXECUTIVE=true
```

When enabled at application startup, the existing authenticated CEPIO public
host mounts an **administrator-only** preview. A trusted actor with
`cepio_admin` must be supplied by the host, and `evaluated_at` is mandatory
for reproducible evidence evaluation. The host mounts:

```text
POST /experimental/performance/v0.1/executive/preview
```

Request shape:

```json
{
  "simulation_only": true,
  "financial_node_id": "cepio.reference.drilling-contractor.metric.revenue-leakage",
  "reasoning": {
    "contract_id": "synthetic-rigco.drilling-performance",
    "node_id": "cepio.reference.drilling-contractor.kpi.npt-ratio",
    "subject": {"id": "rig-07", "type": "Equipment"},
    "observations": [
      {
        "node_id": "cepio.reference.drilling-contractor.kpi.npt-ratio",
        "value": 0.10,
        "observed_at": "2026-10-27T12:00:00Z",
        "evidence_refs": ["synthetic://rig07/npt-event-ledger"],
        "source_subject_id": "rig-07"
      }
    ],
    "evaluated_at": "2026-10-27T12:00:00Z"
  }
}
```

The payload above illustrates **shape only**; the actual synthetic demonstration
includes the full supporting evidence set, an active organization contract
registry, authorized Rig 07 object and installed performance response IQ pack.
The endpoint is intentionally excluded from the supported OpenAPI /api/v1 contract.

**Important trust limit:** submitted observations and their URI-looking references
are **caller-supplied and not independently verified**. The output therefore
declares `evidence_status=caller_supplied_unverified` and
`financial_status=observed_unverified` where a metric is present. This
is suitable only for synthetic exploration/testbeds, **not** authoritative
customer decisions. Production acceptance needs evidence binding, subject
identity attestation, trusted connector authorization and provenance.

## Behavioral limits and safeguards

- An actionable directly observed deviation with
  `source_subject_id == subject.id` is required. A merely propagated
  corporate KPI cannot be turned into a Rig 07 Decision.
- Organization scope must equal the host-injected authenticated tenant; neither
  actor identity nor tenant may come from request JSON.
- CEPIO object read authorization still applies.
- A financial observation is displayed only for an explicitly selected
  currency KPI or metric with valid measured evidence; no EBITDA loss,
  attribution, discounted cash flow or contractual entitlement is inferred.
- Missing financial/HSE/well-control evidence remains missing/unknown.
- The output does not select a corrective action or claim root cause.
- `authority=recommend_only`, `policy_required=true`,
  `causal_claim_made=false`,
  `decision_persisted=false`, `workflow_started=false`,
  `action_executed=false`.

## Qualification and next gate

Unit and REST adapter tests use the synthetic Rig 07 performance fixture
from PR #309, with intentional actor/tenant and source-subject negative cases.

The next milestone is to replace caller-supplied observations with
**tenant-authorized server-side evidence materialization** and then qualify
a live authenticated Copilot/Teams host and Industry IQ Studio consumption.
Only after this can the preview become a production Decision surface.
