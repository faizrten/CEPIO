# CEPIO Main Branch Governance v1

## Purpose

Quality automation is extended by [Code Quality & Governance v2](code-quality-governance-v2.md).
That document corrects the check-name setup below using observed GitHub API names.
The v2 solo-maintainer model still requires zero approvals and no merge queue;
multi-maintainer controls discussed here remain future options.

`main` is the trusted integration branch for CEPIO. Changes should reach `main` only after the repository has proved that the change is reviewable, traceable and compatible with CEPIO's architecture and release claims.

This governance profile is intentionally optimized for a solo maintainer today while remaining suitable for a future multi-maintainer project.

## Operating model

```text
issue / maintenance reason
        -> feature branch
        -> pull request
        -> CEPIO Governance check
        -> CEPIO CI
        -> required checks green
        -> merge / auto-merge
        -> main
```

Direct development on `main` is not part of the normal workflow.

## Repository-owned controls

The repository contains:

- `.github/CODEOWNERS` for accountable ownership;
- `.github/pull_request_template.md` for issue, architecture, validation, IP, documentation and compatibility review;
- `.github/workflows/governance.yml` for automated PR metadata validation;
- `.github/workflows/ci.yml` for CEPIO runtime, API, ontology, generalization, packaging and container qualification.

## Required GitHub repository settings

These settings must be configured once in the GitHub UI because they are repository administration controls rather than repository files.

### 1. Enable auto-merge

Go to:

`Settings -> General -> Pull Requests`

Enable:

- **Allow auto-merge**
- **Always suggest updating pull request branches** (recommended)

Keep the existing merge methods for Governance v1. Merge strategy can be standardized separately without coupling it to branch protection.

### 2. Create the `main` ruleset

Go to:

`Settings -> Rules -> Rulesets -> New ruleset -> New branch ruleset`

Use:

- **Name:** `main-governance-v1`
- **Enforcement status:** `Active`
- **Target branches:** include `main` only (or target the default branch)
- **Bypass list:** none for normal operation

Enable these rules:

1. **Restrict deletions**
2. **Block force pushes**
3. **Require a pull request before merging**
   - required approvals: `0` while CEPIO has a single maintainer;
   - require conversation resolution: enabled if presented in this section;
   - do not require code-owner approval yet, because the sole CODEOWNER cannot provide independent approval of their own PR.
4. **Require status checks to pass before merging**
   - require the current CEPIO CI job: `CEPIO CI / test` (GitHub may display the check context as `test`)
   - require the governance job: `CEPIO Governance / governance` (GitHub may display the check context as `governance`)
   - require branches to be up to date before merging: recommended
5. **Require conversation resolution before merging** if available as a separate rule.

Governance v1 deliberately does **not** require merge queue, signed commits, independent approvals or linear history. Those controls should be introduced when the contributor model justifies them.

## PR governance contract

Every PR targeting `main` must state:

- the linked issue, or a justified `N/A` maintenance reason;
- the change class;
- architecture/semantic impact;
- validation evidence;
- IP/publication classification;
- documentation impact;
- breaking-change/migration impact;
- release/product-claim impact.

The automated `CEPIO Governance` check validates the stable metadata contract. It is not a substitute for CI or architectural review.

## CEPIO architecture invariants

A PR should not merge if it violates any of these boundaries without an explicit, reviewed architecture decision:

1. CEPIO Core remains source-system neutral.
2. Customer/source-specific semantics stay in profiles, mappings, adapters or fixtures unless reusable evidence supports canonical promotion.
3. Agents and applications do not bypass CEPIO identity, policy, Action Runtime, workflow governance or audit.
4. External side effects pass through governed Action/adapter/writeback paths and are verified/reconciled.
5. A source-system field or customer term is not sufficient evidence for a new canonical concept.
6. Public-repository changes must satisfy the CEPIO IP/publication policy.

## Solo-maintainer policy

Governance v1 uses automated evidence rather than a fake reviewer requirement. Until an independent maintainer exists:

- PR required: yes;
- CI required: yes;
- governance metadata required: yes;
- CODEOWNER assigned: yes;
- independent approval required: no.

When CEPIO gains another qualified maintainer, Governance v2 should enable at least one approval for changes to `src/cepio`, `ontologies`, `openapi`, `policies`, `.github`, and governance documents.

## Normal automation path

Once auto-merge and the ruleset are enabled, a normal CEPIO change can use this flow:

1. create a feature branch from current `main`;
2. implement and test;
3. open a PR using the CEPIO template;
4. enable auto-merge;
5. GitHub blocks the PR while required checks are pending or failing;
6. GitHub merges automatically after all required rules are satisfied.

The maintainer should not need to remember whether a PR is safe to merge; the repository should encode the minimum acceptable proof.

## Future Governance v2 triggers

Revisit this profile when any of the following becomes true:

- more than one regular contributor is merging to `main`;
- parallel PR merge contention becomes common;
- CEPIO begins publishing production releases;
- customer deployments depend directly on `main`;
- security/compliance requirements mandate independent approval or signed provenance.

Likely Governance v2 additions: independent approval, path-sensitive CODEOWNER teams, merge queue, release environments, security scanning, dependency review, artifact provenance and deployment approvals.
