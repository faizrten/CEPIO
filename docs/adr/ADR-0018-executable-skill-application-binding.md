# ADR-0018 — Executable Skill binding through the CEPIO Application Contract

## Status

Accepted for Application Contract v0.2 implementation.

## Context

Application Contract v0.1 established protocol-neutral envelopes for Skill invocation/evaluation, Decisions and Actions, but did not execute Skills. CEPIO already had separate runtime capabilities for Skill preflight, deterministic Functions, Decision persistence, governed Actions and READY-only host dispatch.

Without a canonical execution binding, REST, MCP, SDK or other hosts could independently implement Skill procedures and gradually diverge in policy handling, actor identity, evidence lineage or Decision semantics.

The first executable reference is maintenance deferral because its runtime contract is already qualified and its authority boundary is explicit: `ai_agent_recommender` may recommend and propose the bounded maintenance-deferral Decision but may not execute `DeferWorkOrder`.

## Decision

1. Add `CEPIOApplicationService.evaluate_skill` as the protocol-neutral application entry point for explicitly named Skill evaluation.
2. Re-run actor-aware `SkillRegistry` preflight on every invocation; static binding never implies runtime admission.
3. Add `SkillExecutorRegistry` to map a stable READY Skill identity to one executable procedure. Duplicate executable bindings fail closed.
4. Give executable procedures a restricted `SkillExecutionHost` instead of raw `CEPIORuntime` access.
5. The restricted host exposes actor-scoped reads and policy-authorized deterministic Function invocation only in v0.2.
6. Executable Skill code may return a `DecisionProposal` but may not assign creator identity or persist the Decision directly. The application service injects the trusted actor and uses the existing Decision runtime path.
7. Skill evaluation does not execute operational Actions. Recommendation and Action execution remain separate authority domains.
8. Add `assessment_refs` to `SkillInvocation` so governed assessment/uncertainty lineage can survive execution without copying source payloads.
9. Preserve and deterministically merge evidence/assessment references into `SkillEvaluation`.
10. Bind `cepio.skill.maintenance.assess-maintenance-deferral` as the first executable reference procedure using the already-qualified `evaluateMaintenanceDeferralRisk` capability.
11. Do not add or alter REST, MCP or SDK endpoints in this increment. Protocol convergence follows after the execution kernel qualifies.

## Maintenance-deferral execution boundary

```text
SkillInvocation
      |
      v
READY preflight as ai_agent_recommender
      |
      v
maintenance-deferral procedure
      |
      +--> governed object reads
      +--> evaluateMaintenanceDeferralRisk
      |
      v
DecisionProposal
      |
      v
CEPIOApplicationService.propose_decision
      |
      v
persisted maintenance-deferral Decision

DeferWorkOrder execution: NOT performed by the Skill
```

The procedure relies on the existing deterministic function to validate Equipment→WorkOrder and Equipment→Risk identity. It does not create a new engineering risk model.

## Consequences

### Positive

- REST, MCP and SDK can later project one Skill execution behavior rather than reimplementing it.
- Authenticated actor identity remains host-injected.
- Existing Skill preflight remains authoritative.
- Function and Decision policy are re-used, not duplicated.
- The reference Skill can demonstrate industrial reasoning-to-Decision continuity while preserving human/governed Action authority.
- Evidence and assessment lineage survive the application boundary.
- Source/provider bindings remain outside the application contract.

### Trade-offs

- v0.2 supports explicitly named Skill invocation, not generic trigger discovery/ranking.
- The restricted execution host is intentionally small; future Skills may require governed graph traversal, state/provenance reads or other capabilities before they can be bound safely.
- The maintenance risk assessment remains a typed transient Function result unless another runtime capability persists it as a governed object.

## Rejected alternatives

### Give Skill executors raw runtime access

Rejected because it would permit procedures to bypass actor-aware read policy, Function authorization or future host invariants.

### Let each protocol implement Skill execution

Rejected because it would make REST/MCP/SDK separate semantic implementations and violate the application-contract architecture.

### Allow the AI recommender to execute `DeferWorkOrder`

Rejected because the qualified Skill authority contract explicitly declares recommendation/handoff only. v0.2 must not weaken the recommend-before-act boundary.

### Persist a new assessment ontology object solely for v0.2

Rejected. The existing risk Function returns a typed assessment, but introducing a new canonical semantic type requires independent semantic justification. v0.2 exposes the assessment as structured output and preserves existing governed references instead.

## Validation

The increment must pass existing CEPIO governance, architecture, compatibility, security, domain and coverage gates and add deterministic tests for READY admission, blocked actors, executable binding, function authorization, invalid governed evidence, Decision identity, evidence lineage and non-execution of the WorkOrder Action.

## Follow-up

- add governed context assembly/application-contract v0.3;
- expose `evaluate_skill` through REST, MCP and SDK without semantic duplication;
- add cross-protocol conformance tests;
- expand the restricted Skill host only when a qualified Skill requires additional governed capabilities.
