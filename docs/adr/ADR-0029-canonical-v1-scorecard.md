# ADR-0029 — Canonical v1.0 completion scorecard

- Status: Accepted
- Date: 2026-10-20
- Scope: product-roadmap governance, maturity scoring, evidence discipline

## Context

CEPIO development has accelerated across Core, Industry IQ, bindings, assurance, deployment and developer tooling. Release gates remain explicit, but the program no longer has a single canonical numerical statement of progress toward v1.0.

Without a governed scorecard, roadmap maturity can drift between conversations, documentation, issue status, open pull requests and merged capability. That creates product-governance debt: progress can be overstated, duplicated infrastructure can appear equivalent to differentiated Industry IQ, and release readiness can be conflated with implementation activity.

A historical scorecard draft existed in PR #196 but was never merged and referenced an older repository snapshot. The current repository has materially advanced since that draft.

## Decision

Establish `config/v1-scorecard.yaml` as the canonical numerical source of CEPIO v1.0 maturity.

The scorecard uses a fixed 100-point model aligned to the portable Industrial Operating Intelligence North Star:

> CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.

The model is grouped into:

1. Foundation / Core;
2. v0.5 Platform Portability;
3. v0.6 Industry IQ v1;
4. v0.7 Assurance + Generalization;
5. v0.8 Enterprise Profiles + Native Deployment;
6. v0.9 Multi-Enterprise Portability;
7. v1.0 Production Guarantees.

The initial canonical baseline is **69/100** against main commit `a179e9cfc0dbf5e866a6a6aa143eb4290e79918d`.

## Authority separation

The scorecard does not replace release qualification.

- Release gates/manifests remain authoritative for whether a product version is qualified.
- `config/v1-scorecard.yaml` is authoritative for numeric v1.0 completion.
- Roadmap/wiki documents explain sequencing and intent but must not invent a different completion percentage.
- Scheduled reports are read-only projections plus drift detection; they cannot silently mutate the canonical score.

## Evidence rules

Every earned point requires structured evidence.

Evidence may count only when its state is `merged`, `qualified` or `main`. Open PRs may be visible in the scorecard but must use `counts_toward_score: false`.

Partial credit requires an explicit `credit_basis` that states what is independently proven and what substantive proof remains.

A score regression is required when counted evidence becomes invalid, is withdrawn without equivalent replacement, or is shown to have been overstated.

Protected or customer-confidential content must not be copied into the public scorecard. Protected CEPIO-Labs work may be referenced only at a safe abstraction level.

## Anti-gaming rule

Points reward progress toward portable Industrial Operating Intelligence: reusable Industry IQ, evidence/provenance, governed decision/action/outcome paths, provider/model portability, enterprise specialization, assurance, multi-enterprise reuse and production guarantees.

Generic infrastructure duplication does not earn maturity points merely because it increases implementation volume. It counts only when needed to prove a concrete CEPIO operating-intelligence contract or release gate.

## Validation

The scorecard is validated by `scripts/v1_scorecard.py` and repository tests.

Qualification fails when:

- available points do not equal exactly 100;
- stage/gate totals disagree;
- baseline points do not equal earned points;
- earned points lack counting evidence;
- open/unqualified evidence is marked as counting;
- partial credit lacks a credit basis;
- qualified/planned lifecycle state conflicts with earned points;
- the evidence snapshot is not pinned to an exact git SHA.

The new governance document at `docs/governance/v1-scorecard-governance.md` defines the change workflow and evidence-drift policy.

Existing CI, Quality Gate, Governance, governance-protection, compatibility, security and CodeQL controls are not weakened.

## Consequences

Positive:

- roadmap completion becomes reproducible and auditable;
- open work can no longer inflate canonical maturity;
- accelerated parallel development has one shared progress model;
- release qualification remains distinct from maturity;
- scorecard drift becomes observable and actionable;
- North-Star work is rewarded over generic platform complexity.

Trade-offs:

- score updates require explicit PRs rather than conversational estimates;
- the score may regress when evidence is invalidated;
- point-weight changes require explicit product-governance rationale;
- some protected evidence can only be referenced at a safe abstraction level.

## Follow-up

Future roadmap reporting should consume the canonical scorecard, report delta versus the prior canonical revision, identify evidence drift and propose—but never silently apply—score changes.
