# ADR-0014: Refinery operating-abstraction qualification as a permanent CI gate

- Status: Accepted
- Date: 2026-10-18
- Decision owner: CEPIO engineering governance
- Related issue: N/A — refinery Phase 7 qualification slice

## Context

Refinery Phases 1–6 established and normalized the semantic foundation for process operations, reliability, planning, quality, environmental evidence and energy performance. The normalized refinery semantic benchmark reached full coverage, but semantic completeness alone does not prove the CEPIO North Star: an enterprise industrial operating abstraction must reconstruct operational context, ground decisions in evidence, enforce authority and policy, execute governed actions and retain outcomes without becoming the customer's system of record.

The product roadmap already defines K-201 as the CEPIO v0.5 lighthouse for this transition. That release gate ultimately requires a live chain from PI evidence through CEPIO reasoning, policy and approval into a verified SAP write-back. Before attaching live customer or source-system endpoints, CEPIO needs a deterministic, source-neutral qualification that proves the operating-abstraction contract itself.

Because this qualification is intended to remain a merge regression for refinery evolution, the refinery CI lane must be extended. `.github/workflows/ci.yml` is a protected governance path, so the change requires explicit high-risk review and an ADR.

## Decision

Add **Refinery Operating Abstraction Qualification v0.1** as a permanent fail-closed refinery CI gate.

The gate has three layers:

1. **Frozen semantic contract** — five critical refinery operating questions covering abnormal operations, K-201 reliability/work/spares, planning and movements, quality disposition, and energy/environmental performance.
2. **Runtime evidence contract** — deterministic synthetic fixtures must materialize and traverse the required cross-domain graph, resolve expected properties, cite only current evidence and reject fabricated evidence identifiers fail-closed.
3. **K-201 governed-action lighthouse** — a synthetic source-neutral external action must prove direct AI write denial, contextual approval, prohibition of AI self-approval, exactly-once dispatch, exactly-once verification, idempotent replay, retained policy evidence and a verified `WorkflowOutcome`.

The source-neutral external adapter is intentionally named `synthetic_sap` and uses CEPIO's fake governed-write adapter. This phase must not claim live SAP, PI or customer-system qualification.

## CI topology

The existing `ci-refinery` lane is extended with two commands:

- semantic qualification for `generalization/competency/refinery-operating-abstraction-v0.1.yaml`;
- runtime/governed-action qualification through `scripts/run_refinery_operating_qualification.py`.

Both reports are included in the existing refinery evidence artifact. No existing refinery, drilling, contract, package, container, quality, governance or CodeQL gate is removed or weakened. The stable required aggregate context remains `test`, consistent with ADR-0013.

## Invariants

- Existing refinery semantic baselines remain frozen and continue to run.
- Existing drilling qualification remains unchanged and required.
- The normalized refinery semantic benchmark remains required.
- The operating-abstraction gate is additive and fail-closed.
- No customer data or customer-specific endpoint is introduced.
- No new ontology vocabulary is introduced by this phase.
- AI actors cannot bypass the existing CEPIO action authorization model.
- High-risk governed actions require the configured human approval authority.
- External writes remain idempotent and require verification before a verified workflow outcome can be recorded.
- `test`, `quality-gate`, Governance, governance-protection and CodeQL remain required merge contexts.

## Validation

The implementation must demonstrate:

- five of five operating-abstraction semantic questions pass;
- five of five runtime questions pass with 100% runtime evidence coverage;
- direct AI-only `CreateWorkOrder` is denied;
- policy pauses the K-201 workflow for human approval;
- an AI actor cannot approve its own intervention;
- the authorized maintenance manager can approve;
- the synthetic external write is dispatched exactly once;
- external verification occurs exactly once;
- replay is idempotent;
- policy evaluation evidence is retained on the action audit;
- a verified `WorkflowOutcome` is produced;
- full CEPIO CI, Quality Gate, Governance and CodeQL remain green.

## Consequences

### Positive

- refinery work now has an executable North Star qualification rather than ontology coverage alone;
- future refinery changes must preserve evidence-grounded, governed and auditable behavior;
- the K-201 live integration proof can focus on real PI/SAP bindings rather than re-proving generic operating-abstraction mechanics;
- customer-system boundaries remain explicit.

### Trade-offs

- the refinery CI lane performs additional deterministic qualification work;
- the synthetic lighthouse proves CEPIO behavior but cannot be cited as live industrial integration evidence;
- future changes to policy, Kinetic or external-action contracts may require coordinated updates to this qualification.

## Non-goals

This decision does not close the CEPIO v0.5 live industrial integration release gate, certify SAP or AVEVA PI connectivity, introduce customer-specific ontology/profile content, add a refinery UI, or authorize autonomous high-risk industrial actions.
