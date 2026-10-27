# ADR-0047: Solo-founder risk-proportionate pull request review (P0)

Status: Proposed (requires review and existing governance qualification)

## Decision

Keep GitHub Actions and all existing branch, governance, security, quality, IP-publication, deployment, and budget controls. Do not introduce a required second human approval for ordinary changes when the only maintainer is the author. Introduce a read-only trusted-base PR risk-triage workflow to recommend R0–R3 classes, without permission to merge, publish, deploy, change labels, or modify repository rules.

As an initial measurable reduction of PR administration, allow a minimal governance description **only** when GitHub's changed-file API confirms that every file is a non-deleted, non-renamed `README.md` or ordinary `docs/` file outside `docs/adr/` and `docs/governance/`, and the PR explicitly selects **low** risk. The streamlined body must still include a meaningful summary, a risk selection and the existing public-IP classification. The independent `governance-protection` workflow is unchanged and remains a required check.

All other pull requests retain the original mandatory sections, change classification and linked-issue rules. In particular, changes to `.github/`, protected policy, API, ontology, persistence, identity, deployment, infrastructure, and security surfaces are never eligible for this docs-only exception.

## Risk tiers (advisory, not authorization)

- R0: narrowly allowlisted documentation additions and updates (outside governance and ADRs).
- R1: regular deterministic tests, examples and scenario/evaluation assets; assess content and provenance before merge.
- R2: new or changed code and semantic contracts not automatically classed as critical; technically significant and subject to existing gates.
- R3: workflows, security, authorization, identity, tenant isolation, production deployment, provenance, database migrations, budgets, dependency manifests, and other protected surfaces.

Unknown paths default conservatively to R2. Deletions, oversized PRs and renames do not receive lower scrutiny. Triage reads the GitHub PR files API from `pull_request_target` without executing untrusted head code and has read-only token permissions. It is informational; it does not change review rules or automatically merge PRs. Classifications can be overridden upward after content inspection, never used to waive existing safeguards.

## Rationale

CEPIO currently has a single founder/operator and a broad existing set of mandatory GitHub checks. Mandating an independent approval for every PR would either stall delivery or incentivize insecure exceptions, while lengthy metadata requirements on harmless documentation changes consume scarce founder time. Risk-based triage and a very narrow documentation shortcut save review administration while preserving CI and authorization boundaries.

## Validation and rollout

1. Test the streamlined template with a documentation-only PR, verify required `governance`, `governance-protection`, `quality-gate`, `test`, and `security-codeql` still pass.
2. Test negative cases: source-code change with `low` checkbox, workflow change, governance/ADR documentation, rename, deletion, or unspecified/medium/high risk must use original requirements.
3. Confirm published PR content remains subject to the existing public-IP review; do not assume a path-based checker validates actual data contents.
4. Keep rollout fail-closed. Do not change main ruleset, required check names, branch protections, deployment authorization, paid inference, or infrastructure grants as part of this ADR.

## Rollback

Revert the optional triage workflow and the eligibility/streamlining change in `.github/workflows/governance.yml`; all other required governance and release protections remain unchanged.
