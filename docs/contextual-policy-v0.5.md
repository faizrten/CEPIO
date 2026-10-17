# CEPIO Contextual Policy v0.5

CEPIO Policy v0.5 introduces a first-class, version-addressable policy contract for governed industrial execution. It is additive to the existing role-based policy engine: current RBAC, read filtering, function permissions and decision-proposal permissions remain valid while contextual action policy is introduced on top.

## Design objective

The policy plane must answer more than `can this role execute this action?`. It must be able to consider:

- actor identity, role and delegated authority;
- governed action or function;
- subject/resource type and semantic properties;
- action parameters;
- operating context and risk state;
- evidence metadata and confidence;
- required obligations such as approval, evidence or a Decision record.

The first implementation slice is deliberately deterministic, side-effect free and source-neutral.

## Core contracts

`PolicyDefinition` is immutable and identified by `(id, version)`. A `PolicyRegistry` resolves that exact pair and rejects mutation of an already registered version.

A definition contains:

- `PolicyScope` — action, function and resource-type applicability;
- ordered `PolicyRule` contracts;
- `PolicyCondition` expressions;
- a `PolicyEffect`;
- optional `PolicyObligation` records;
- an explicit default effect.

The current effects reuse the stable CEPIO vocabulary:

- `allow`
- `recommend_only`
- `approval_required`
- `deny`

The current obligations are:

- `require_evidence`
- `require_approval_authority`
- `require_decision_record`

## Evaluation context

Conditions resolve against a bounded document:

```text
actor.id
actor.roles
action.type
action.parameters.*
function.name
subject.id
subject.type
subject.properties.*
context.*
evidence.*
```

The first supported operators are:

```text
eq
neq
gt
gte
lt
lte
contains
in
not_in
exists
```

Conditions within a rule are ANDed. Multiple matched rules are combined using deny-dominant precedence:

```text
allow < recommend_only < approval_required < deny
```

Multiple policy definitions use the same precedence. This means adding contextual policy cannot silently weaken an existing control.

## Fail-closed behavior

A governed condition that cannot be evaluated because required context is missing or incompatible is `indeterminate`. An in-scope policy with an indeterminate rule fails closed to `deny` and records the reason in `PolicyEvaluation` evidence.

This is intentional for industrial execution. Missing risk, operating-state or evidence inputs must not be interpreted as permission.

`exists` is the exception because absence is the condition being tested explicitly.

## Evidence-rich evaluation

`PolicyEvaluation` records:

- final effect;
- human-readable reasons;
- obligations;
- exact policy references evaluated;
- matched rule IDs;
- per-rule condition evidence;
- whether any result was indeterminate.

This result can be persisted or attached to workflow/action audit lineage in a later slice without changing policy semantics.

## Compatibility with the existing engine

`ContextualPolicyEngine` wraps an existing `PolicyEngine` such as `RolePolicyEngine`.

For runtime actions:

```text
legacy RBAC decision
        +
exact contextual policy versions
        ↓
deny-dominant composition
```

A contextual `allow` never overrides a legacy `deny`. A contextual `approval_required` can raise a legacy `allow` to an approval gate.

For this first slice, object read policy, property filtering, function authorization, decision-proposal authorization and action capability preflight delegate to the legacy engine. Capability preflight therefore proves base authority; instance-specific contextual policy is evaluated again at runtime when the target, parameters, risk and evidence are available.

## Representative high-risk maintenance policy

Conceptually:

```yaml
id: high-risk-maintenance-approval
version: 1.0.0
scope:
  actions: [CreateWorkOrder]
  resource_types: [Compressor]
rules:
  - id: high-criticality-high-risk
    priority: 100
    when:
      - subject.properties.criticality in [high, safety_critical]
      - action.parameters.risk_score >= 0.7
    effect: approval_required
    obligations:
      - require_approval_authority: maintenance_manager
      - require_evidence
      - require_decision_record
default_effect: allow
```

The explicit `allow` default is safe because it is still composed with the existing action RBAC decision.

## Version pinning

Callers reference a policy using `PolicyReference(policy_id, version)`. No implicit latest-version resolution is used for governed execution.

This prepares the workflow runtime for a critical invariant:

> A running or paused workflow must resume against the same policy version under which it was admitted unless an explicit migration is performed.

Workflow-level persistence of policy references is the next integration slice; this initial implementation establishes the immutable contract and exact resolver first.

## Current boundary

Implemented now:

- immutable versioned policy contracts;
- deterministic conditions and effects;
- obligations;
- evaluation evidence;
- fail-closed indeterminate handling;
- policy registry and exact version resolution;
- deny-dominant composition with the existing policy engine;
- runtime action compatibility;
- qualification tests.

Not yet implemented in this slice:

- persistent policy repository;
- workflow definition/instance policy-reference pinning;
- automatic runtime context/evidence provider injection;
- contextual read/function/decision policy;
- policy authoring API or UI;
- policy simulation/dry-run service;
- policy evaluation persistence in AuditEntry;
- external OPA/Cedar policy adapters.

## Recommended next slice

1. Add policy references to `WorkflowDefinition` and persist them on `WorkflowInstance`.
2. Persist `PolicyEvaluation` identity/evidence with governed Action and workflow audit lineage.
3. Add a runtime `PolicyContextProvider` that derives operating state, risk and evidence from CEPIO canonical state rather than trusting arbitrary client-supplied context.
4. Extend policy to workflow steps and approvals.
5. Expose policy simulation/explanation before adding authoring UI.

The desired control path becomes:

```text
Event / API / Agent
        ↓
WorkflowDefinition + pinned PolicyReference(s)
        ↓
canonical state + evidence
        ↓
PolicyEvaluation
        ↓
allow | recommend | approval | deny
        ↓
Decision / Approval / Action
        ↓
External verification
        ↓
Outcome + audit lineage
```
