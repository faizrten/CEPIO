# Runtime-aware Skill preflight

## Purpose

Static Skill binding answers whether a logical dependency has an explicit CEPIO runtime identity. It does **not** prove that the Skill can safely run for a particular actor.

v0.2.2 adds a runtime-aware `SkillRegistry` preflight boundary before planner dispatch.

```text
Skill package
    |
resolved binding
    |
    v
SkillRegistry
    |
    +-- preflight(runtime, actor)
            |
            +-- READY   -> eligible for host dispatch
            |
            +-- BLOCKED -> no planner invocation
```

Preflight is a host/runtime concern. It is deliberately **not** exposed as an Operator tool: an agent must not decide whether it is authorized to invoke itself.

## What READY means

A Skill is `READY` only when every applicable check passes:

1. **Canonical identity** — bound object types and relationships are canonical registered CEPIO identifiers; functions, Decisions and Actions exist.
2. **Graph reachability** — declared evidence paths satisfy relationship domain/range semantics, including inverse traversal.
3. **Evidence visibility** — the actor may read required evidence and every intermediate/target type used by a declared graph path.
4. **Function authorization** — the actor may invoke every required CEPIO function.
5. **Decision authority** — the Skill declares proposal authority and the actor may propose each required named Decision.
6. **Action authority alignment** — runtime policy must match the Skill's procedural authority. A recommend-only Skill is blocked when executed under an actor that could directly execute the action.
7. **Auditability** — Decision-to-Action causal linkage must be representable in governed audit records when the Skill uses both Decisions and Actions.

`READY` proves capability and policy eligibility. It does not prove that a specific target currently has enough data to answer a question. Invocation-time evidence sufficiency remains the Operator's responsibility and continues to fail closed.

## Authority rule

The preflight boundary checks both under-authorization and over-authorization.

For example, the reliability Skill declares `CreateWorkOrder` as recommendation/handoff only. Under `ai_agent_recommender`, CEPIO policy returns `recommend_only`, so the action check passes. Under `maintenance_engineer`, policy returns `allow`; preflight blocks with `ACTOR_EXCEEDS_SKILL_AUTHORITY` because the actor is more powerful than the Skill contract permits.

This prevents a compromised or erroneous planner from converting a recommendation-only procedure into execution merely because the selected runtime identity has broader privileges.

## Graph-path validation

A Skill declares semantic paths using logical identifiers. The preflight evaluator resolves those identifiers through the binding map and validates each hop against the TypeRegistry.

For equipment failure history:

```text
Equipment
  <- failureOfEquipment - FailureEvent
  - hasFailureMode -> FailureMode
```

The inverse first hop is validated using `FailureEvent` as the relationship domain and `Equipment` as the range. A shortcut such as `Equipment -hasFailureMode-> FailureMode` is rejected even though all three identifiers individually exist.

## API

```python
registry = SkillRegistry(runtime)
registry.register(spec)

result = registry.preflight(
    spec.skill_id,
    actor_id="skill-agent-1",
    actor_roles={"ai_agent_recommender"},
)

if result.status == "READY":
    # host may dispatch the Skill
    ...
```

Every check returns a stable reason code and message. `BLOCKED` is fail-closed: any failed check prevents host dispatch.

## Scope

v0.2.2 is a capability-and-policy preflight. It does not yet perform target-instance freshness checks, trigger classification, model selection, Skill conflict arbitration or dynamic tool-health probing. Those remain separate host/runtime concerns.


## v0.2.3 READY-only dispatch

The host uses `cepio.dispatch_skill` with candidates produced by the static binder.
Every invocation filters static BOUND candidates, evaluates actor-aware preflight
against the current runtime, then matches triggers only against READY identities.
Only one match dispatches. Zero ready candidates returns `NO_READY_SKILL`; ready
candidates with no trigger match return `NO_MATCH`; multiple matches return
`CONFLICT` with sorted identities and no Operator invocation. Registration order
is never a tie breaker. Duplicate identities and malformed BOUND contracts raise
a configuration error before matching. Preflight errors propagate without dispatch.

This is a synchronous host integration contract: trusted callbacks must preserve
the same runtime and actor and must not mutate policy during matching. Do not
cache READY results or dispatch from a previously returned selection. Preflight
stays outside MCP/REST Operator tools. READY proves capability and authority, not
case evidence: the Operator must still return `INSUFFICIENT_CEPIO_EVIDENCE` when
required governed evidence is absent. Governed execution rechecks action policy.
