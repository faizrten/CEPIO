# ADR-0012: Deletion-aware coverage regression gate

- Status: Accepted
- Date: 2026-10-18
- Decision owner: CEPIO engineering governance
- Related issue: #163

## Context

CEPIO requires coverage evidence on pull requests. The original gate compared only the repository-wide coverage percentage between the immutable PR base and the head. That is intentionally strict, but an aggregate percentage is sensitive to code-mix changes: deleting production code together with obsolete dedicated tests can lower the percentage even when no surviving production behavior loses coverage.

As CEPIO development accelerates, the coverage gate must continue to prevent untested behavior and test erosion without making legitimate deletion, modularization, or repository-boundary cleanup unnecessarily difficult.

## Decision

Keep full-suite base and head coverage collection, but replace aggregate percentage as the sole merge criterion with a deletion-aware regression contract.

A pull request must satisfy all of the following:

1. absolute uncovered production-line debt must not increase;
2. previously covered production lines that are unchanged by the pull request must not become uncovered, including unchanged lines inside a modified file;
3. changed executable production lines must meet a minimum 90% diff-coverage threshold;
4. aggregate base/head coverage percentages remain recorded as evidence, but a percentage decrease caused only by deletion or code-mix effects is not independently merge-blocking;
5. the checker emits machine-readable evidence for review and audit.

The protected `quality-gate` remains required. Full pytest, architecture, compatibility, security, CodeQL, governance, and product/domain qualification are unchanged.

## Rationale

This policy is stronger than a numeric tolerance because it tests the behaviors we actually want to protect. A tolerance can hide real regression within an allowed percentage band. The deletion-aware contract instead fails newly uncovered surviving code and insufficiently tested changed code while permitting safe removal of code that no longer exists.

The rule is intentionally repository-wide for production Python. It is not a changed-files-only substitute for full qualification.

## Validation

The implementation is qualified by focused regression tests proving that:

- deleting fully covered production code can pass even when aggregate percentage changes adversely;
- new untested production code fails;
- well-tested new production code passes;
- removing tests that expose unchanged production behavior fails;
- insufficient changed-line coverage fails;
- new coverage cannot numerically mask coverage loss on an unchanged line in the same modified file.

The normal protected-main workflows remain authoritative and must all pass before merge.

## Consequences

### Positive

- safe code deletion and modularization do not create false coverage blockers;
- new/changed production behavior receives an explicit high coverage requirement;
- coverage erosion on surviving behavior remains fail-closed;
- reviewers receive both aggregate and change-aware evidence.

### Trade-offs

- the quality job still executes coverage on both base and head, so this ADR improves correctness rather than CI duration;
- diff parsing and path normalization become part of the quality-gate implementation and therefore require regression tests;
- CI wall-clock optimization is handled separately by #170 rather than weakening this gate.

## Governance invariant

This ADR changes coverage evaluation semantics only. It does not remove a required check, introduce `allow_failure`, lower the full-test requirement, or create a path-based exemption from merge qualification.
