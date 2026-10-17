# ADR-0009: Pin workflow policy and trusted evaluation evidence

Status: Accepted

## Decision

Bind workflow policy references at instance creation, resolve only exact versions, and evaluate at the Action boundary through a host-configured trusted context provider. Persist evaluation and approval evidence with workflow history, Action audits, external execution records and Outcomes.

## Context

Policy v0.5 evaluates immutable definitions but does not bind them to durable workflows. Caller-provided risk context cannot serve as trusted operational evidence. Approval must survive restart without silently adopting newer policy semantics.

## Consequences and controls

RBAC and action policy compose by the most restrictive effect before idempotent replay or handler execution. Missing context, stale observations, unknown policy versions and missing boundary configuration fail closed. Approval fingerprints bind canonical object versions and policy evidence; changed state requires another approval. AI roles cannot approve. Waiting for approval does not consume retry attempts. Existing external identity, dispatch, reconciliation and verification gates are preserved.

Existing JSON records gain defaulted additive fields, with no table migration or package-version change. Ordinary execute_action, SDK and HTTP request contracts are preserved. The trusted guarded execution entry point is not exposed to clients. Hosts reload exact policy definitions and reinject the provider on restart. Source observation freshness remains an explicit provider responsibility.

## Validation

Policy v0.5.1 regression tests cover SQLite restart with a newer registered policy, trusted-context failures, approval authority and invalidation, basic/resilient execution, and verified external Outcome evidence. Existing kinetic, policy, architecture, API/client, compatibility, security and full CI gates remain enforced.
