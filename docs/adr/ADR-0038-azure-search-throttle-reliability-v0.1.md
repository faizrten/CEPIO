# ADR-0038 — Azure AI Search Bounded Indexing Reliability and Scale Qualification

- **Status:** Superseded by ADR-0039 (2026-10-22); historical record only
- **Date:** 2026-10-22
- **Decision owners:** CEPIO retrieval/platform engineering
- **Related:** ADR-0032 Azure AI Search adapter; GitHub qualification runs 39430176053 and 39593038395

## Context

On 20 October the qualification failed on Search index-management HTTP 403.
After correcting Azure Search RBAC, the 21 October live run successfully
reached synthetic document uploads but failed with HTTP 429 ("too many
requests"). The earlier tool pushed batches of 1,000 documents with no
application-level pacing or bounded retries; it discarded its evidence JSON
when the step failed. A 500K default is an unnecessary expense and
operational risk while a 5K smoke has not passed.

## Decision

1. The Azure Search index remains a **rebuildable projection** of the CEPIO
   MemoryStore and Capability Registry; it never becomes an authority.
2. Search index projection writes may retry HTTP 429, 500, 502, 503, 504
   only. Stable document IDs make retried upserts idempotent. No request
   with a 401/403 or permanent per-document rejection is retried.
3. Retry only transiently failed documents when a partial result supplies
   per-document statuses. Incomplete results fail closed. Retries are
   limited to seven total attempts with bounded exponential backoff
   (up to 30s) and numeric Retry-After support.
4. The GitHub **azure-demo** qualification workflow defaults to
   **5K then 50K**, hard caps corpus size at 50K, limits uploads to
   100 records per batch with 0.5s pacing, and serializes future
   qualification workflows against the development Search index.
5. Emit bounded, synthetic-only JSON PASS/FAIL evidence in both successful
   and failed runs. Record progress, retry count, result IDs and query
   latency; never invent scale proof from successful authentication.
6. Dev Search index creation/reset remains an explicit, human-approved,
   OIDC-authenticated workflow operation. Never automatically increase
   cloud capacity, elevate roles, bypass tenant filters, or access
   production/customer indexes during qualification.

## Governance and safety

The workflow path is protected by the CEPIO governance gate; this ADR
documents the protected workflow modification without relaxing checks.
Tenant visibility/expiry checks, required evidence, and explicit authority
checks remain unchanged. No customer data, IP-sensitive Industry IQ
knowledge, API keys, secrets, or credentials are published.

Old *waiting* workflow runs (created without the new concurrency group)
can reset the index when subsequently approved, so they must be cancelled
before a fresh live qualification. The new concurrency group protects only
runs based on the updated workflow.

## Validation and rollback

Deterministic unit tests cover transient exception retry, Retry-After,
partial success, retry exhaustion and immediate permanent rejection.
CI security, governance, architecture and coverage gates must pass.
The live 5K test must pass before the 50K progression can be called
qualified; 50K success does not establish a production SLO.

Rollback reverts the adapter retry policy and scale workflow change, but
the former 1,000-document unpaced ingestion must not be used as evidence
of production readiness. A capacity increase needs separate expenditure
approval and actual throughput evidence.
