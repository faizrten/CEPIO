# ADR-0014: Fail-closed warning policy with narrow upstream quarantine

- Status: Accepted
- Date: 2026-10-18
- Decision owner: CEPIO engineering governance
- Related issue: #164

## Context

CEPIO's full test suite was functionally green but emitted a very large warning volume dominated by one repeated RDFLib/pySHACL deprecation. A warning flood makes CI less useful because new deprecations, resource warnings and runtime warnings can disappear into background noise.

The current CEPIO validation implementation passes ordinary RDFLib `Graph` instances into pySHACL and does not directly call the deprecated `Dataset.default_context` API. The repeated warning is emitted by the currently resolved RDFLib/pySHACL dependency path.

As development accelerates, warnings should behave like other quality signals: unexpected warnings must fail qualification, while unavoidable third-party noise may be quarantined only through a precise, reviewable exception.

## Decision

Configure pytest to fail on warnings by default using `filterwarnings = ["error", ...]`.

Permit one temporary exception only for the exact upstream warning:

`Dataset.default_context is deprecated, use Dataset.default_graph instead.`

The exception is constrained by:

- exact warning message;
- `DeprecationWarning` category;
- originating module `rdflib.graph`.

Global suppression such as `ignore::DeprecationWarning` is prohibited.

The warning policy is treated as a protected engineering-governance surface. Any new exception requires normal review, a narrow filter and documented ownership/removal rationale.

## Validation

Qualification must prove both sides of the contract:

1. the committed pytest warning list begins with `error` and contains only explicitly reviewed narrow exceptions;
2. an unrelated warning emitted by a test causes pytest to fail;
3. the existing full CEPIO test, SHACL, architecture, compatibility, security and domain qualification suites remain green;
4. the exact upstream quarantine does not alter SHACL validation semantics.

The regression test launches an inner pytest process that emits an unrelated `RuntimeWarning` and asserts that the run fails. This proves the policy is fail-closed rather than merely documenting an intention.

## Removal criteria

The RDFLib quarantine must be removed when the resolved dependency path no longer emits the warning. Dependency-upgrade PRs run the full qualification suite and should delete the exception as soon as it is unnecessary.

## Consequences

### Positive

- CI warning output becomes high-signal;
- new deprecations and runtime/resource warnings become immediate merge blockers;
- third-party exceptions are explicit and auditable;
- dependency upgrades can demonstrably reduce the exception set.

### Trade-offs

- dependency upgrades may surface new warnings that require upstream fixes, CEPIO code changes or a narrowly justified temporary quarantine;
- contributors may need to resolve warnings that previously did not block development.

## Non-goals

This decision does not pin obsolete dependencies to hide warnings, suppress all third-party warnings, weaken SHACL validation, or replace dependency/security qualification.
