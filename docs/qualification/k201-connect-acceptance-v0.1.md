# K-201 CONNECT qualification: source-and-Action acceptance matrix (proposed)

**Status:** DRAFT ACCEPTANCE CONTRACT — NOT QUALIFIED, NOT AUTHORIZED FOR LIVE EXECUTION  
**Prepared:** 2026-11-19 (Asia/Riyadh)  
**Source baseline:** `faizrten/CEPIO` main `738467348039263cbbbb654422b61c570efc3858`  
**Governing release issues:** [v0.5 CONNECT #51](https://github.com/faizrten/CEPIO/issues/51), [K-201 #58](https://github.com/faizrten/CEPIO/issues/58), [SAP #53](https://github.com/faizrten/CEPIO/issues/53), [PI #54](https://github.com/faizrten/CEPIO/issues/54), [common writeback #57](https://github.com/faizrten/CEPIO/issues/57).

## Purpose and authority

Freeze the **minimum independently inspectable evidence** for qualifying a single, source-authoritative K-201 industrial operating loop. This is a release acceptance plan, **not** an implementation claim, approval to access industrial data, instruction to issue a work order, or maturity-score update. `RELEASE.md` and #51 retain release authority.

Do **not** copy customer data, industrial procedures, source record contents, credentials, hidden evaluator labels, or protected Industry IQ methods into this public document. Protected scenarios, prompts and blind assessments stay in appropriately permissioned locations. All live identifiers and verification artifacts are recorded in an authorized private evidence ledger; public reporting uses permission-reviewed, sanitized attestation references.

## Required sources — one real asset, three *meaningful* domains

| Required source domain | Required industrial contribution | Read-only acceptance | Qualification status |
| --- | --- | --- | --- |
| AVEVA PI / historian (#54) | Source-authoritative condition measurements/events and asset/tag identity | Authenticated host read; source identifier, quality/status, unit, event time, ingestion time, mapping version and freshness; reject invalid/ambiguous evidence | **NOT VERIFIED LIVE** |
| SAP S/4HANA EAM (#53) | Equipment / functional location and maintenance-work context; authoritative write target | Authenticated read of maintenance record/version with canonical-asset match and provenance; preserve source-owned transaction authority | **NOT VERIFIED LIVE** |
| Third independent source, selected by an authorized system owner | A materially different decision input: e.g. Fabric enterprise production context, OSDU engineering/subsurface context, or P6 schedule context | Authenticated read of a genuinely independent record relevant to the **same asset and decision**; identify original source-of-truth rather than double-counting a SAP/PI replica | **SOURCE NOT YET SELECTED OR VERIFIED** |

The third source is *not* qualified merely by connector registration, a second database storing a copy of another record, or a source record unrelated to the evaluated Decision. The integration lead and source owners must identify the exact real source and permission boundary before any live test.

## Acceptance phases and artifacts

| ID | Gate | Minimum pass evidence | Hard refusal / negative control |
| --- | --- | --- | --- |
| **KC-00** | **Permission and environment preflight** | Written authorized non-production target, scope, named accountable source owners, approved actor/workload identity, approved read/write actions, permitted source data use, rollback and retention; exact app/image/contract versions recorded | Missing consent, unknown role, unauthorized data export, production target or unapproved spend = **NO RUN** |
| **KC-01** | **Three-source observational truth** | Three current, authenticated, materially relevant source-domain reads for one canonical asset; external IDs, mapping version, valid/source/ingestion times, source record versions, provenance and source-quality flags | Wrong asset, wrong tenant, missing/expired rights, stale/conflicting evidence, absent source quality, duplicated system-of-record evidence = **BLOCK** |
| **KC-02** | **Deterministic replay and identity** | Saved rights-cleared replay manifest reconstructs the same normalized asset/state and refusal outcomes from captured, versioned observations; no implicit type/alias promotion | Ambiguous external identity or changed/superseded source version without revalidation = **BLOCK** |
| **KC-03** | **Industry IQ treatment** | Authenticated CEPIO host/policy/Skill READY preflight; versioned pack and Skill IDs; actual governed invocation receipt with evidence IDs, policy and actor lineage | Pack name in a prompt, synthetic result, inapplicable method, missing required evidence or model-asserted roles is **NOT a treatment PASS** |
| **KC-04** | **Reviewable Decision** | Evidence-grounded observations, competing hypotheses, uncertainty, supported options, accountable reviewer and immutable Decision identity; explicitly marked recommendation-only before approval | Unsupported root cause, fabricated source, uncertain limit presented as certainty, invalid permit or wrong-shift identity = **BLOCK** |
| **KC-05** | **Governed permitted SAP Action** | Separate explicit approval for exact maintenance notification/order transaction; host-derived identity/tenant/permission, policy and human approval; idempotency key and preconditions linked to Decision; action exclusively through #57/Action Runtime | Direct LLM/agent/provider write, stale approval, changed material evidence, target/version conflict or duplicate external dispatch = **BLOCK** |
| **KC-06** | **Read-back, reconcile, Outcome** | Independent authoritative SAP readback of resulting record/status and version; write receipt, verify/reconcile state, immutable `WorkflowOutcome`, actor/Decision/Action/workflow/source correlation and audit; failure/retry replay tests | Transport ACK alone or an uncertain write outcome is **NOT SUCCESS**; no blind redispatch; explicit reconciliation required |
| **KC-07** | **Adversarial and failure qualification** | Frozen negative-test suite for wrong actor/tenant/asset/shift, missing/denied source, stale records, revoked rights, conflicting evidence, permit/task mismatch, approvals after evidence change, timeout/ambiguous commit and repeat idempotency | Any unauthorized action, fabricated evidence, incorrect provenance or safety-policy bypass is a **hard failure**, regardless of overall test rate |
| **KC-08** | **Independent release review** | Integration lead + domain-competent reviewer + security/authority reviewer assess exact-version evidence; redacted public release record states successes, failures, unknowns and limitations | CI PASS, source connectivity, synthetic scenarios or one successful write **alone** do not authorize release qualification |

The proposed matrix is source-neutral: reuse the existing [Binding Contract](../developer/platform-bindings.md), canonical CEPIO identity/time/provenance, Skill admission, contextual policy, governed Action Runtime and immutable Outcome. Do **not** implement a second connector SDK, agent execution engine, Action dispatcher, temporal store or generic workflow platform.

## Non-negotiable identity, authority and replay behavior

1. External source records remain authoritative for their own fields and transactions. A canonical asset match requires approved, versioned mappings; name similarity is never sufficient.
2. Host identity and policy are evaluated **before** data exposure and before external effect. A model request does not supply its own roles, source authority or approval.
3. Missing/conflicting evidence can yield bounded `INSUFFICIENT_EVIDENCE` or `AMBIGUOUS` findings with next checks, but must not trigger a source write or a false diagnosis.
4. An issued permit is **not** permission to perform work; check current work/task/shift authorization under responsible customer policy.
5. Material evidence revision invalidates decisions/approvals that depend on the superseded evidence unless independently reauthorized.
6. If the external write outcome is unknown, record `VERIFY_PENDING` / `RECONCILIATION_REQUIRED` under the existing runtime semantics and independently check SAP before any retry.
7. Preserve source-use rights, tenant isolation, revocation and retention across stored evidence and reproducible investigation artifacts. No derived customer intelligence becomes globally reusable by default.

## Evidence manifest (private/permissioned, not embedded here)

Each actual qualification run must generate or point to a versioned, independently reviewable manifest containing **at least**:

- exact Core / Labs / Studio revisions, deployed image digest, adapter versions, contract/policy revision, scenario/Skill/pack revisions;
- environment classification, approved access scope and accountable source/reviewer roles (no credentials or identifying secrets);
- canonical asset ID, three authoritative domain classes, mapping/version lineage and sanitized source-reference hashes;
- event/source/ingestion timestamps, measurement quality/freshness, rights/tenant decisions and relevant denials;
- evidence-readiness result, Skill READY and actual host invocation receipt, Decision ID and approved authority ceiling;
- approved external action identity, idempotency key, external source acknowledgment and independent source readback;
- reconciliation outcome, immutable Outcome reference, replay result, failure tests and complete audit correlation;
- explicit evidence tier: **synthetic conformance**, **independent offline**, **authenticated live-source** or **field-validated**, with scope limits;
- signed/approved reviewer verdict, open risks, valid-until date and invalidation/retest triggers.

**Redaction:** A public status record may cite a reviewed attestation digest or sanitized claim; it must not disclose protected Labs evaluations, customer source records, access credentials, identity claims or proprietary industrial reasoning.

## GO / NO-GO decision

- **Current verdict: NO-GO / NOT QUALIFIED.** This document freezes proposed acceptance criteria only. Current public evidence does not establish KC-01, KC-05 or KC-06 live success.
- **Before any real test:** source owner authorization, permitted read/write boundaries, exact target and operator agreement are required. No deployment, provisioning, role/permission change, paid inference or customer-data handling is authorized by this document.
- **v0.5 release qualification:** only after KC-00 through KC-08 pass within a declared, reviewed scope and #51/#58 are formally closed through normal release governance.
- **Scorecard:** this plan earns **zero** maturity points; v1 remains at its separate canonical baseline, v2 is not assessed.

## Coordination

- Public gate owners: #51, #53, #54, #57, #58 and #326.
- Protected independent K-201/R3 competence qualification remains under permissioned Labs issue #235. Do not copy its cases, methods, evaluator materials or reviewer identities into public trackers.
- W1/W2 workspace/readback features remain separate from SAP authority; a saved work item or source snapshot is not a CEPIO Decision or permission to operate.
