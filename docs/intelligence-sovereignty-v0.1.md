# Intelligence Sovereignty Contract v0.1 — enforcement slice

**Status:** PR candidate / not a production qualification.  
**Tracking:** [CEPIO #299](https://github.com/faizrten/CEPIO/issues/299).  
**Authority:** ADR-006, ADR-007 and ADR-0044.  
**Published release / scorecard:** unchanged (v0.4 Developer Preview; governed 69/100 baseline).

## Boundary

`cepio.sovereignty.IntelligenceSovereigntyContract` is a source-neutral rights assertion, not a new tenancy service or an authorization source of truth. An assertion identifies its source, owner, class, tenant (if customer-owned), licensing/consent reference, permitted uses, reviewer reference, expiration/revocation timestamps, and derivative parent IDs. The v0.1 use verbs are `TENANT_INFERENCE`, `TENANT_ADAPTATION`, `SHARED_RETRIEVAL`, `GLOBAL_LEARNING`, `EVALUATION` and `EXPORT`.

**Fail-closed rules for registered sources:** a missing, untrusted, expired, revoked, cyclic or restricted parent permission denies use. Customer and customer-derived sources cannot be used for shared retrieval or global learning, even if a synthetic identifier or asserted global-learning verb is attached. Derivatives must carry parent source IDs and every ancestor must independently permit the requested use. A human review reference is required for global learning, evaluation or export. Merely declaring a reviewer string does not validate a human identity.

## Enforced integrations in this PR

| Surface | Implemented guard | Current limit |
| --- | --- | --- |
| `MemoryRecord` + `RetrievalEngine` | Records tagged with `sovereignty_source_id` are checked after each backend response, before fusion or context assembly. Hosts that call `configure_source_rights(..., require_source_tags=True)` also reject untagged records. Declared contributing `provenance.source_ids` are checked together. Customer evidence requires matching tenant and `TENANT_INFERENCE`; GLOBAL memory requires `SHARED_RETRIEVAL`. Missing rights drop the hit. | Historical untagged GLOBAL memory continues to use existing legacy GLOBAL semantics. Full catalog backfill and authorization on direct `MemoryStore` calls remain outstanding. |
| Capability promotion | Evidence tagged with a sovereignty source is checked for `GLOBAL_LEARNING` across all declared capability `provenance.source_ids` using a rights snapshot supplied separately from the promotion candidate. The original `evaluate_promotion` entry remains backwards compatible and denies tagged evidence without rights; the new `evaluate_promotion_with_rights` is an opt-in host integration that rejects any untagged or missing evidence and incomplete source provenance before approving global promotion. Existing cross-domain, regression and human approval gates remain. | Legacy untagged evidence can still be promoted under historical source-neutral contracts. Full source manifest enforcement and trusted approval artifact validation remain outstanding. |
| Compiled Industry IQ | **Not modified in this public PR.** The protected implementation stays out of public CEPIO as required by IP governance. | Source-use enforcement at compilation and cached activation, including revocation and expiry, must be qualified privately in Labs before production use. |

**Trusted inputs:** The rights mapping must come from an independently authorized, versioned enterprise/CEPIO record or deployment configuration; never the model, a retrieved document, an API caller's privilege claim or the promotion candidate. Missing mapping for a tagged source denies use. The new contract is frozen, extra-field rejecting, and revalidated before a grant is used; this does **not** authenticate the record issuer. This PR does **not** provide a rights-ingestion workflow, signature verification, reviewer identity reconciliation, or hosted configuration. No actual tenant-rights source has been validated in Azure. Source-reference tags must be propagated to all relevant memory and capability records before production qualification.

## Direct-memory authorization candidate (stacked milestone)

`SovereignMemoryStore` is an **opt-in wrapper** over the existing `MemoryStore` protocol. A trusted host supplies an already-authenticated principal (`actor_id`, `tenant_id`) and a callable source-rights provider. The wrapper binds all operations to that tenant rather than accepting caller-selected tenant IDs. On every read, write or query, it obtains a fresh rights snapshot and checks all declared provenance source IDs and inherited parent grants against the current wall clock. Missing tags, incomplete lineage, revoked/expired permissions, cross-tenant writes, and unavailable rights providers fail closed. Shared-memory reads require `SHARED_RETRIEVAL`, tenant writes require `TENANT_ADAPTATION`; shared-memory publication is deliberately refused. Tenant erasure remains possible after rights revocation, subject to the separate host action policy.

**Trust boundary and limits:** this library wrapper neither authenticates the host nor proves consent/grant authenticity. The sole allowed caller is a verified host that maps an Entra/Studio actor to the correct CEPIO **customer-data tenant**, which need not be identical to the Entra issuer tenant. Do not expose arbitrary `SovereignMemoryStore` construction or rights-provider configuration to a client or model. The underlying storage reference must not be shared with untrusted callers; production requires storage-level tenant isolation and a trusted, independently verified source-rights issuer. Grants are refreshed at operation boundaries, not atomically with backend transactions: cross-process revocation/TOCTOU still requires a durable authority and transaction-bound enforcement. Query filtering does not attest upstream embedding/index isolation, prompt/evaluation/export isolation or direct access paths that bypass this adapter.

No production host uses this wrapper in this milestone. It introduces no PostgreSQL grants, cloud resources, paid model inference, external side effects or customer-data access. Treat it as a contract-level negative qualification step, not a production-isolation claim.

## Boundary inventory and next work

- **Ingestion and bindings:** existing provider-neutral binding and source provenance contracts; attach trusted source identifiers at ingestion, validate ownership and authorization, and reject untagged customer-derived artifacts before they reach durable storage.
- **Memory and retrieval:** tagged runtime outputs are checked; migrate historical untagged source identities, enforce at direct MemoryStore/index/graph/vector boundaries, and verify tenant identity comes from Entra/CEPIO identity rather than caller strings.
- **Prompts, traces and caches:** assembled context inherits retrieval restrictions, but compiled-cache source-rights enforcement remains pending in the protected lane. Audit all prompt/tracing/export sinks for redaction, retention, and cross-tenant isolation; reject raw customer content in shared caches.
- **Evaluation and global promotion:** add trusted source-grant loading, derivative lineage verification, independent source rights and disclosure review; prohibit tenant-only records from shared evaluation, training and export pipelines.
- **Synthetic data:** customer-derived analogues retain all ancestral restrictions; independent protected Labs scenarios and held-out truth remain in Labs. Synthetic renaming alone conveys no release rights.
- **Source actions:** existing policy, actor authorization, idempotency and audit rules remain authoritative. Sovereignty is not a replacement for policy enforcement.

## Qualification and operations

Run `pytest -q tests/test_intelligence_sovereignty.py` plus normal CEPIO CI, Quality, CodeQL and Governance. Negative tests exercise denied source permissions, expiry, revocation, missing or cyclic lineage, cross-tenant retrieval, customer-derived synthetic promotion, AI-approval rejection and mixed-source lineage denial; cached-bundle revocation is an outstanding protected qualification.

**Not claimed:** host-enabled strict mode or complete ancestry from authoritative ingestion (no verified host binding exists), fully enforced enterprise-wide data egress, hosted rights verification, customer opt-in to shared training, PostgreSQL migration, production multi-tenancy, enterprise audit assurance, production release or scorecard advancement.

**Exit from PR-candidate to release-ready feature** requires mandatory source tagging of the relevant ingest/promotion paths, verified rights authority, source-scoped audit, complete ingress/egress coverage and hosted negative test evidence. Keep #299 open until those gates and Labs private qualification succeed.
