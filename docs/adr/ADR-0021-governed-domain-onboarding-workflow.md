# ADR-0021 — Governed Domain Onboarding Workflow

- Status: Accepted
- Date: 2026-10-19
- Decision owners: CEPIO architecture / Industry IQ

## Context

CEPIO has now onboarded and qualified materially different industrial domains through recurring Generalization Lab patterns: scope an archetype, define personas and competency questions, freeze the benchmark, baseline the existing canonical model, distinguish semantic equivalence from true gaps, classify those gaps, qualify runtime evidence, and review reusable capabilities for promotion.

Keeping this sequence as an informal methodology would allow domain-specific implementation paths to diverge and could weaken CEPIO's reuse, profile-isolation and fail-closed governance principles.

## Decision

CEPIO will treat domain onboarding as a versioned control-plane workflow governed by explicit policy.

`workflow.domain-onboarding.v1` defines the lifecycle:

`REQUESTED -> SCOPED -> BENCHMARKED -> BASELINED -> GAP_ANALYZED -> QUALIFYING -> QUALIFIED -> GENERALIZATION_REVIEW -> RELEASE_CANDIDATE -> RELEASED`.

Policy thresholds and allowed gap dispositions are versioned separately from the state machine. The initial policy requires a frozen benchmark, complete gap classification, zero critical qualification failures, deterministic runtime evidence, and human review before promotion or release.

The canonical gap vocabulary for this workflow is `CORE`, `COMMON`, `DOMAIN`, `MAPPING`, `PROFILE`, and `REJECT`.

The workflow reuses the existing deterministic Generalization Harness and runtime-evidence coverage implementation; it does not introduce a second ontology evaluator. Repository artifacts remain the v0.1 execution boundary. A later Kinetic binding may persist long-running control-plane instances, but it must preserve the same workflow and policy gates.

## Governance boundary

Automated execution may advance only through `GENERALIZATION_REVIEW`. CI must not infer architecture approval, promote domain semantics into Industrial Common/Core, or release a domain. Those transitions remain explicit human policy decisions.

Artifact paths are repository-bounded and validation fails closed. If the baseline exposes semantic gaps, every current gap must be covered exactly once by an accepted triage pack before qualification can continue; stale, duplicate, missing, or unsupported classifications block execution.

## Consequences

Positive:

- subsequent Industry IQ domains share one auditable onboarding contract;
- benchmark immutability and baseline evidence become first-class gates;
- cross-domain generalization can be reviewed from a consistent Domain Delta report;
- customer/profile semantics are less likely to leak into canonical layers;
- workflow policy can evolve independently from domain implementation code.

Trade-offs:

- the first version is stricter than the previous informal process;
- fully new domains may legitimately stop at `BLOCKED` until gap triage and remediation are complete;
- v0.1 does not yet provide a durable Kinetic workflow instance or automatic remediation.

## Validation

The first canary backfills the existing Refinery operating-abstraction qualification. The dedicated Domain Onboarding CI lane executes the governed runner and focused contract tests. A successful reference run must show 5/5 semantic competency passes, 100% semantic-check pass rate, zero semantic gaps, 100% runtime coverage, and terminate at `GENERALIZATION_REVIEW / READY_FOR_HUMAN_REVIEW`.

Existing CEPIO CI, quality, governance, CodeQL, domain qualification and release gates remain enforced; the new workflow adds a qualification surface and does not bypass or weaken any existing gate.
