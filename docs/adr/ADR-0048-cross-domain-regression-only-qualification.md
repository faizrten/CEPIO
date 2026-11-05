# ADR-0048: Strict cross-domain regression-only qualification routing

**Status:** Proposed for review (no general-purpose bypass)
**Date:** 2026-11-03
**Classification:** PUBLIC architecture / governance contract
**Related:** Issue #320; cross-domain regression PR #319; ADR-0046 Core-only domain onboarding qualification; approved CEPIO Product North Star.

## Context and requirement

The Domain Onboarding workflow expects exactly one changed domain-pack manifest when changed files concern domain generalization. A frozen, cross-domain regression manifest is an independent *testing artifact*, not a new domain being onboarded. Requiring an invented manifest would obscure provenance, defeat explicit admission controls, and expand the ability to promote competence without proper qualification.

The first case is an explicitly public and synthetic reference mapping an evidence-change / decision-reassessment pattern across two existing frozen Industry IQ runtime fixtures (K-201 reliability and Reservoir R3). It does not introduce new industrial know-how, a production capability, or an authorization to change any enterprise system.

## Decision

Introduce a **single bounded regression-only CI route** for the fixed evidence-decision-reassessment v0.1 manifest and its dedicated automated tests.

1. Only the exact public regression manifest, dedicated tests, scope validator, this ADR, the explanatory reference document and the Domain Onboarding workflow are admitted. This is a version-specific allowlist—not a broad glob or discretionary bypass.
2. Diff records must have status A or M, without deletions, renames, duplicate paths, unknown changes or mixed Core/domain/ontology/policy/sensitive-code mutations. Unknown scope fails closed.
3. Both the designated manifest **and** its negative-control test must be present in the changed set.
4. Run the pre-existing frozen two-target cross-domain regression with 100% survival, then the new public evidence/provenance regression and policy-router negative tests. The same underlying CEPIO runtime coverage evaluator remains the authoritative engine.
5. Only when that specific route qualifies may the ordinary Domain Onboarding job omit the requirement for a new domain-pack manifest.
6. New/updated domain packs still require the existing full Domain Onboarding, persona ICC, compounding and human-governed promotion path. Core-only changes keep their separate previously accepted qualification route.

No change to CEPIO Core semantics, authorization, customer knowledge isolation, canonical scorecard, production environment, or v0.5 CONNECT release requirements is authorized by this ADR.

## Security, governance and publication

- No customer data, credentials, live source access, production-action capability, proprietary casebook, or sealed evaluation material in this public change.
- No new generic agent framework, simulator, database, model runtime, or scenario execution platform.
- Protected Industry IQ methods, evaluator scoring logic, future unseen holdouts and customer-scoped knowledge stay in CEPIO-Labs or the relevant customer boundary.
- The public implementation is limited to a strict CI routing contract required to preserve the existing governance boundary.
- Adding further regression families or admission paths requires a separate policy review and ADR; do not loosen the allowlist by silently broadening a path glob.
- GitHub's governance-protection job, quality/static/CodeQL checks, and any branch review requirements remain authoritative. A successful deterministic fixture does not qualify a Skill, an AI judgment or a production deployment.

## Explicit negative tests

Tests must reject: no manifest, no designated test, an arbitrary second regression manifest, any new domain pack, changed ontology, changed runtime or policy, edits to unrelated CI, removal/rename/unknown diff statuses, and duplicate paths. Positive admission requires both fixed files and only the exact allowlist. The complete scoped regression must pass. CI remains free to fail for other unrelated quality/security concerns.

## Alternatives rejected

- **Create a fictitious domain pack for a cross-domain test:** obscures source of competence and may inadvertently trigger domain-promotion machinery.
- **Skip the Domain Onboarding workflow for all regression paths:** introduces a broad exception with no independent assurance.
- **Add another generic scenario/evaluation platform:** duplicates existing CEPIO runtime coverage and Industrial Evals capability with no demonstrated product benefit.
- **Place proprietary holdouts into public CEPIO:** violates the Core/Labs IP boundary and undermines independent evaluation.

## Validation and qualification limits

The PR must pass the existing checks and prove that mutation of a required evidence/consequence link fails the deterministic runtime test. The new routing path is only *CI scope admission*. It is not a claim of Industry IQ uplift, independently reviewed expert competence, successful actual CEPIO agent execution, verified source-system writeback, or v0.5/v1.0 advancement.

Accepted implementation remains subject to the usual PR review and release governance.

## Memory contract routing correction

The existing memory contract test file is already executed in Core qualification
but was omitted from the Core-only changed-path allowlist. Admit the exact
`tests/test_memory_context.py` path alongside `src/cepio/memory.py`.
This correction retains the mandatory frozen cross-domain suite and all Core
contract tests. It introduces no additional regression family or path glob.
Validation includes task-context negative cases, the complete memory suite,
and successful Domain Onboarding qualification on PR #341.
