# Workflow policy integration v0.5.1

Workflow definitions accept a tuple of exact `PolicyReference(policy_id, version)` values. Starting an instance copies those pins into its durable JSON payload. Both memory and SQLite repositories preserve them, alongside the immutable workflow definition version. Existing payloads default to an empty tuple and retain their previous behavior. No SQL schema migration is required.

Configure the trusted host boundary before starting or resuming a governed workflow:

```python
from cepio import PolicyRegistry, WorkflowPolicyBoundary

kinetic.workflow_policy = WorkflowPolicyBoundary(
    PolicyRegistry([high_risk_policy_v1, high_risk_policy_v1_1])
)
```

Register definitions with `policy_references=(high_risk_policy_v1.reference,)`. Loading a newer policy into the registry never changes an existing instance. Reload all referenced definitions and configure the boundary again after process restart. Missing boundaries, unresolved versions, or pins inconsistent with the stored workflow definition fail closed before action execution.

## Trusted context and obligations

`PolicyContextProvider.for_action(request, target)` returns a `TrustedPolicyContext`. The default `CanonicalPolicyContextProvider` uses canonical object properties as `context`, with object identity and version as evidence. Workflow inputs and caller parameters cannot override this context. Action parameters remain available under `action.parameters` for policies that intentionally govern the requested operation; use `context` or `subject.properties` for trusted operational risk.

A custom provider may derive risk, evidence and observation timestamps from trusted CEPIO projections or other host-owned canonical state. It must enforce the freshness of its underlying evidence sources. The boundary checks subject identity, object version, timezone-aware observation time, and maximum context age (60 seconds by default). The default provider timestamps the canonical read; this does not prove upstream sensor freshness. Express upstream freshness in the provider when required.

Matched evidence obligations require nonempty trusted evidence. Decision obligations require a persisted Decision. Approval-authority obligations use an explicit `role` parameter; every required role must be held by the approving human. An approval effect without a declared authority fails closed. AI roles cannot approve, even when combined with a human authority role. Unsupported or missing obligation requirements fail closed through the deterministic evaluator/provider boundary.

## Approval and execution

A contextual approval requirement pauses the current Action step and creates a durable approval task. Approval resumes that same step, rather than skipping its Action. A SHA-256 fingerprint binds approval to the evaluated versions, conditions, canonical object version, trusted context/evidence, and action parameters. Changed canonical state or policy evidence requires a new approval. Approval never overrides RBAC, recommend-only roles, existing action approvals or preconditions.

The trusted host-only `execute_guarded_action` entry point evaluates contextual policy together with ordinary action policy before the idempotency cache or handler. REST, SDK and MCP callers cannot provide a guard. The ordinary `execute_action(request)` contract is unchanged. Both basic and resilient workflows use the guarded path; waiting for approval does not consume a retry attempt.

## Durable lineage and external verification

Each contextual evaluation has an ID, time, workflow/step identity, exact references, condition results, matched rules, effects, obligations and trusted source evidence. `kinetic.history(instance_id)` exposes `policy_evaluated` records. Action results and immutable action audits include `policy_evidence`, including the consumed approval ID and final composed effect. Replayed actions are re-evaluated and receive fresh audit evidence before cache lookup.

External execution records copy the initiating Action's policy evidence, and terminal Workflow Outcomes retain the action audit evidence. The chain is queryable by workflow instance, action ID and external execution ID. External dispatch, unknown-outcome reconciliation, identity-drift checks and source verification retain their existing contracts: local Action success never substitutes for verified source-system success.

The boundary is a trusted in-process host integration. Authentication and actor-role attestation remain the responsibility of the existing API/host authorization boundary. Policy evaluation is side-effect free; runtime coordinators own approval, execution, retries, external writes and Outcome recording.

## Qualification

`tests/test_workflow_policy_v051.py` covers SQLite restart, exact version pinning while paused, approval authority, AI rejection, canonical context isolation, stale/missing context, provider failures, RBAC/deny composition, changed-state approval invalidation, and Action → external verification → Outcome lineage for basic and resilient workflows.
