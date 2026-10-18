# ADR-0013: Parallel qualification topology with stable merge contexts

- Status: Accepted
- Date: 2026-10-18
- Decision owner: CEPIO engineering governance
- Related issue: #170

## Context

CEPIO's merge qualification has become intentionally broad: full unit/runtime tests, public-contract validation, drilling and refinery qualification, packaging, container smoke, security, architecture, compatibility, CodeQL and deletion-aware coverage evidence all participate in the protected-main decision.

The quality of that validation is desirable, but the original topology serialized too much independent work. `CEPIO CI` ran unit tests, domain harnesses, package smoke and container smoke inside one long job. The Quality Gate collected full head coverage and then full immutable-base coverage sequentially. On the first real consumer of ADR-0012 (#175), the two coverage suites each took roughly 83 seconds, making the serial coverage pair a significant part of the merge-critical path.

Accelerating development should reduce waiting and duplicated setup work, not reduce what must be proven before merge.

## Decision

Parallelize independent qualification work while preserving stable required status contexts as the governance facade.

### CEPIO CI

The internal CI workflow is split into independent lanes:

- `ci-unit` — full pytest suite;
- `ci-contracts` — Skill dispatch/preflight, query baseline, deployment validation, API/client/ontology contracts, deterministic validation and demo;
- `ci-drilling` — all existing drilling/generalization qualification;
- `ci-refinery` — all existing refinery/process qualification;
- `ci-package` — wheel build and installed-wheel smoke test;
- `ci-container` — container build and health smoke test.

A final aggregator remains named exactly `test` and succeeds only when every lane succeeds. The branch rules therefore retain the same required `test` context while work executes concurrently behind it.

### Quality Gate

Static, architecture, compatibility and security lanes remain independent. Coverage is split into:

- `quality-tests-head` — full head test suite with coverage;
- `quality-tests-base` — full test suite at the immutable PR base SHA with coverage;
- `quality-coverage-compare` — consumes both coverage artifacts and runs the unchanged ADR-0012 deletion-aware comparison.

The final aggregator remains named exactly `quality-gate`. On pull requests it requires all quality lanes, including both coverage collectors and comparison. On push/workflow-call events, where no immutable PR base exists, base/comparison lanes are skipped and the normal head/static/architecture/compatibility/security lanes remain required.

### Caching

Python jobs use `setup-python` pip caching keyed by Python version and the relevant committed dependency inputs. Caches may accelerate dependency retrieval but do not substitute for installation or validation. A dependency-input change invalidates the cache key.

## Invariants

- Every validation previously required by CEPIO CI remains required before a product PR can merge.
- No path-based file filter may skip full merge qualification.
- Drilling and refinery qualification remain fail-closed.
- Packaging and container smoke remain required.
- The ADR-0012 coverage semantics remain unchanged: uncovered production debt cannot increase, unchanged covered lines cannot lose coverage, and changed executable lines require the configured diff-coverage threshold.
- `test` and `quality-gate` remain stable required status contexts.
- Governance, governance-protection and CodeQL remain separate required contexts.
- Parallel execution must not introduce shared mutable state between lanes.

## Rationale

Independent validations should not occupy the same critical path merely because they were originally written in one YAML job. Parallel lanes provide earlier failure localization, permit targeted job reruns where GitHub supports them and reduce wall-clock time without changing the definition of green.

Stable aggregator names are deliberate. Branch governance should depend on a small, durable contract (`test`, `quality-gate`) rather than every internal job name. This allows qualification topology to evolve without silently weakening or constantly rewriting the main ruleset.

Parallel head/base coverage collection is particularly valuable because both runs are deterministic and independent until comparison. Their artifacts are joined only after both complete, so the deletion-aware result is identical in meaning to the prior serial implementation.

## Validation

The implementation must prove that:

- all existing CEPIO CI commands are represented in one of the new lanes;
- the final `test` aggregator fails if any lane fails, is cancelled or is skipped unexpectedly;
- the final `quality-gate` fails if any required quality lane fails;
- PR head and immutable-base coverage are collected independently and compared using `scripts/check_coverage.py` without semantic changes;
- coverage, compatibility, drilling, refinery and package evidence remains uploaded;
- required status contexts observed by GitHub remain `test` and `quality-gate`;
- a representative full PR shows a material wall-clock reduction, with >=40% as the target subject to hosted-runner availability.

## Consequences

### Positive

- substantially shorter merge feedback loops;
- failures surface by concern rather than late in one serial job;
- independent failed lanes can be rerun without conceptually invalidating unrelated evidence;
- dependency downloads are reused safely;
- governance remains insulated from internal CI topology changes.

### Trade-offs

- more GitHub-hosted runners may execute concurrently;
- artifact transfer is required for cross-job coverage comparison;
- workflow YAML is more structured and therefore requires governance tests and ADR discipline;
- total compute minutes may not fall even when wall-clock latency improves.

## Non-goals

This decision does not introduce changed-files-only merge testing, remove full qualification, weaken coverage requirements, create environment-specific exemptions or replace release qualification with fast local checks. Local preflight parity is tracked separately in #171.
