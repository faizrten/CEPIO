# WC-01: Work-cycle contract reuse spike

Date: 2026-11-05. Status: interface assessment completed for the bounded scope below; integration and production qualification remain open.

## Decision

Compose a professional work-context projection above existing CEPIO contracts. Do not add a new canonical Core concept, generic orchestration engine or customer database in this milestone. Reuse existing runtime admission, memory, Decisions and outcomes with explicit application-level completeness and version checks.

This spike validates interfaces and a small memory behavior sample. It is not an implementation of the full work cycle.

## Field-level reuse and boundaries

| Work-context need | Inspected interface | Reuse and necessary addition |
| --- | --- | --- |
| Subject / task | ObjectRef; OntologyObject and existing WorkItem usage | Reference canonical subjects. Add work-context identity and revision in the application projection; do not encode Rig 07 as a product type. |
| Goal / success criteria | PerformanceContract.id/version; PerformanceNode.target, thresholds, scope_subject_id and validity | Reference applicable versioned nodes; allow a provisional user objective without pretending it is an approved performance contract. |
| Responsibility | PerformanceAccountability.subject_id/node_id/relation | Reuse accountability links; add human confirmation and task-specific ownership as separate interaction records. Accountability is not authorization. |
| Technical recommendation | Decision.problem, observations, recommendation, recommended_action, selected_action | Reference Decisions; do not interpret selected_action or textual outcome as approval or verified external success. Link answer revisions and evidence independently. |
| Durable continuity | MemoryRecord; MemoryStore.put/get/query/forget; SQLiteMemoryStore | Reuse scoped memory for summaries and references. MemoryStore.put overwrites and has no expected-revision argument; it is not an immutable work-event ledger or optimistic concurrency contract. |
| Bounded turn context | ContextCandidate.required; ContextAssembler.assemble | Reuse budget/ranking. Add required-evidence completeness check before and after selection; READY is not a supported-answer guarantee. |
| Capability eligibility | RuntimeAdmissionResolver; HostAdmissionServices; HostPrincipal | Principal, roles, evidence verification and eligibility originate in the authenticated host. Never accept these as user/model declarations. |
| Skill admission | SkillRegistry.preflight; SkillPreflightSpec | Reuse registry admission for runtime, policy and declared capability checks. Target-instance evidence sufficiency is explicitly outside preflight's guarantee. |
| Verified external outcome | WorkflowOutcome.workflow_instance_id, definition_version, step_id, subject, action_id, external_execution_id, status, evidence | Reference externally verified workflow outcomes. This schema is unsuitable for a general no-action question outcome; add a separate debrief observation projection rather than inventing an external execution ID. |
| Changed evidence | Existing evidence-to-decision cross-domain reference | Reuse graph-path regression as structural coverage. Its documentation explicitly says it does not prove an agent notices change or revises a recommendation. Add behavioral reassessment evaluation. |

## Confirmed implementation boundaries

1. **Context selection is not evidence completeness.** Expired/invisible candidates are filtered before required-budget checks. An expired required candidate can be dropped while the assembler returns READY. This is a consumer integration hazard, not evidence of cross-tenant leakage.
2. **Memory is not the authoritative audit ledger.** Current put operations permit same-owner replacement; no expected revision is required. Keep decisions/history in the established governed persistence paths. Inspect those repository interfaces before selecting a work-context write adapter.
3. **Preflight is not job readiness.** Its docstring explicitly excludes target-instance evidence sufficiency. Separate capability availability, evidence completeness, job prerequisites and permission to act in both API and UI.
4. **Outcome categories must remain distinct.** Advice usefulness, user-reported completion, simulated results and externally verified action outcomes must not collapse into one success field.
5. **Host admission is an integration boundary.** Existing unit tests use fake Skills and Services to exercise resolver behavior; they do not attest deployed identity, source verification or customer capability eligibility.

## Proposed composition flow for WC-02 / WC-03

1. Resolve authenticated principal and current source-use rights through host-owned services.
2. Load authorized work references and applicable contract versions; check expected work revision.
3. Determine the professional question and its required evidence using Industry IQ.
4. Resolve capability eligibility and run existing Skill preflight.
5. Independently verify target-instance evidence applicability, freshness, conflicts and completeness.
6. Assemble bounded context, then check that required evidence survived selection. Return an unresolved/escalated answer when it did not.
7. Produce a referenced assessment with explicit uncertainty, assumptions and dependencies.
8. Record the assessment through governed persistence; keep recommendation separate from operational authority.
9. On new evidence, rights revocation or requirement change, reassess affected answers and preserve history.
10. Link outcomes and scoped lessons without silently promoting customer knowledge.

## Local verification

Downloaded exact connector-returned memory.py blob a5c0beda6311e71b8de3c2ab39aa793591187d97 into an isolated temporary source subset. No source changes were made.

Attempted the existing tests/test_memory_context.py suite. It could not start because pytest is absent from the local Python environment. No full-suite PASS is claimed.

A standalone Python assertion probe against the unchanged module completed successfully:
- reproduced expired required evidence being omitted with READY and an empty selected set;
- confirmed required context token-budget overflow returns BLOCKED;
- confirmed SQLite close/reopen preserves a tenant record;
- confirmed another tenant cannot retrieve that record.

This validates only the extracted memory module behavior. Package initialization, application integration, CI and deployment were not tested.

## Source evidence

Full source retrieved; selected interface definitions and relevant behavior inspected:
- src/cepio/model.py — Decision, ObjectRef, action/audit records.
- src/cepio/performance_contract.py — blob 825deab885e311ffd0d1be0b2ed9d8e21960a16f.
- src/cepio/memory.py — blob a5c0beda6311e71b8de3c2ab39aa793591187d97.
- src/cepio/kinetic_external.py — blob 118b3838c88fc505594d1f298a71a9dd1eb09d85.
- src/cepio/skill_preflight.py — blob 478db000d71a32d08307916f58a5645ae175d59c.
- src/cepio/accc_host_admission.py — authenticated host services and resolver.
- tests/test_memory_context.py — reviewed; pytest execution unavailable.
- tests/test_accc_host_admission.py — reviewed; not executed.
- docs/evidence-decision-cross-domain-v0.1.md — structural vs behavioral evidence boundary.

No protected Labs contents or customer data are included.

## Next bounded implementation

WC-02 should deliver a versioned read-only projection and synthetic contract tests before persistence writes:
- separate question-answer state, capability admission, evidence completeness and action authority;
- generic work/subject IDs and references to existing contracts;
- valid revision and dependency references, explicit evidence freshness/conflict state;
- no client-supplied actor/tenant/roles/approval flags;
- negative tests for expired/missing evidence, denied scope, changed revision, conflicting requirement and unsupported capability;
- no deployment, paid inference or change to production mutation flags.

Persistence adapter choice, concurrency semantics and source revocation remain open engineering tasks. WC-01 does not qualify them. The four-stage Studio preview can use this projection once its contract is tested.
