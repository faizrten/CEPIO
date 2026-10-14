# Functions, Decisions and Actions

## Why CEPIO models kinetics

A useful industrial ontology must represent not only what things **are**, but what the enterprise can **calculate, decide and do**.

This is the kinetic dimension of CEPIO.

## Function

A function is a typed operation that derives information.

Examples:

- calculate expected production loss from compressor downtime;
- evaluate remaining margin exposure;
- calculate reliability risk score;
- identify dependencies within N hops;
- determine material shortage impact.

Functions should have explicit contracts:

```text
Function
  - name
  - input types
  - output type
  - allowed target types
  - authorization policy
  - implementation binding
```

## Decision

A decision links evidence and reasoning to a recommendation or selected course of action.

A decision record can capture:

- target object;
- evidence references;
- relevant state and time context;
- function outputs;
- recommended action;
- actor/agent;
- confidence or rationale;
- approval state.

## Action

An action changes CEPIO state or invokes an external effect.

Examples:

- create work order;
- request inspection;
- approve maintenance scope;
- issue a procurement request;
- trigger a schedule change;
- acknowledge an alarm workflow.

## Action execution boundary

```text
Request action
   |
Resolve actor + target + action
   |
Policy evaluation
   |
Authorized?
   +-- no -> deny + audit
   |
   v
Idempotency check
   |
Preconditions
   |
Execute CEPIO effect
   |
External adapter if applicable
   |
Record acknowledgement/reconciliation
   |
Immutable audit
```

## Preconditions

Actions may require conditions such as:

- object is in a specific state;
- actor has specific role;
- an approval exists;
- expected object version matches;
- related work item exists;
- maintenance window is active;
- risk threshold is satisfied.

## Idempotency

External enterprise actions must be safe against retries.

Idempotency keys are scoped so one actor cannot reuse another actor's prior successful result to bypass authorization.

## Compensation and reconciliation

Enterprise actions are not always atomic across systems.

CEPIO therefore needs explicit metadata for:

- external acknowledgement;
- retry state;
- reconciliation status;
- compensation guidance where applicable;
- dead-letter handling in production integrations.

## Human and AI operating model

A useful pattern is progressively increasing authority:

```text
Observe
 -> Explain
 -> Recommend
 -> Request approval
 -> Execute bounded action
 -> Observe outcome
```

AI agents should earn operational authority through explicit policy rather than obtain it implicitly because they can access an MCP tool.
