# ADR-0010: Drilling domain-qualification benchmark and validation boundary

Status: Accepted

## Decision

Keep the Drilling Contractor domain-qualification benchmark and its CI workflow
as an additive generalization and validation capability. The v0.4 competency
pack, v0.3 persona pack and v0.4.1 normalization remain outside the canonical
CEPIO ontology. The workflow measures and reports qualification results; it
does not remediate ontology gaps or promote benchmark terms into canonical
semantics.

## Context

The qualification milestone needs a stable, reproducible way to assess whether
the existing source-neutral ontology can answer representative Drilling
Contractor competency questions. Adding domain vocabulary to the canonical
ontology merely to improve a benchmark score would conflate domain coverage
with reusable CEPIO semantics. The raw v0.4 benchmark and normalized v0.4.1
benchmark therefore remain explicit, versioned evaluation inputs, with gap
triage performed before any ontology remediation.

## Consequences and controls

The dedicated workflow runs the frozen-contract regression test, the raw and
normalized qualification harnesses, and publishes their reports as CI
artifacts. It is scoped to relevant benchmark, harness, ontology and workflow
paths. It adds evidence without replacing or weakening existing CI, governance,
quality or CodeQL checks. The trusted-base governance-protection workflow
continues to enforce PR risk classification and protected-path documentation.

Qualification results are evidence for review, not a production readiness claim
or permission to change canonical semantics. Any later ontology remediation
must be separately justified by reusable semantic evidence and pass the
repository's existing ontology and governance controls.

## Validation

The workflow validates the frozen v0.4 contract, runs both benchmark versions
with gap triage skipped, and records deterministic status counts and semantic
check rates in uploaded reports. Regression tests verify benchmark structure,
cross-references, persona coverage and semantic pressure. The ordinary
repository CI, governance, quality and CodeQL checks remain independently
enforced.
