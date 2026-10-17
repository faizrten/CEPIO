# CEPIO Code Quality & Governance v2

Main Governance v1 remains the foundation. This extension keeps approvals at **0**,
conversation resolution, an up-to-date branch, no force pushes/deletions, and no
bypass actors. No merge queue, required owner review, or compliance bureaucracy.

## Merge evidence

| Check-run name | Evidence / enforcement |
| --- | --- |
| `test` | Existing CEPIO CI, unchanged API/client/ontology/generalization/SHACL, wheel and container qualification |
| `governance` | Existing Main Governance v1 PR contract |
| `quality-gate` | Fails unless all five quality jobs succeed; skipped/cancelled jobs cannot satisfy it |
| `quality-static` | Ruff across src/tests/scripts, mypy across src/cepio, formatting touched Python |
| `quality-architecture` | Core/import/profile/write boundaries plus behavioral security regression tests |
| `quality-compatibility` | Accepted baseline gates plus immutable PR-base API/Python/DDL/ontology comparison |
| `quality-security` | Bandit medium/high scan and resolved dependency audit with no vulnerability ignores |
| `quality-tests` | Full suite and coverage that cannot decrease relative to PR base |
| `security-codeql` | Python and GitHub Actions security-extended analysis, also weekly |
| `governance-protection` | Trusted-base risk/IP/ADR checks on protected changes; never executes PR head code |

An AST architecture test is a structural guard, not a sandbox. Behavioral tests
remain authoritative for policy-before-replay, authorization, audit and external
write verification. Customer concepts remain in profile namespaces; canonical
promotions require an ADR explaining cross-customer reuse evidence.

## Exact ruleset changes

In Settings → Rules → Rulesets → `main-governance-v1`, retain every existing
protection and the name. Replace the two incorrectly configured contexts with
the **actual API check-run names**, verified on v1 commit `fc2038f9`:

1. Remove `CEPIO CI / test (pull_request)`; add `test` (GitHub Actions).
2. Remove `CEPIO Governance / governance (pull_request)`; add `governance` (GitHub Actions).
3. After v2 has passed, add `quality-gate` and `security-codeql` (GitHub Actions).
4. Once v2 is on main, open a small follow-up PR to observe and then require
   `governance-protection` (GitHub Actions). A newly introduced
   `pull_request_target` workflow cannot run from the initial PR head.

GitHub UI workflow/event labels are not literal required check contexts. Select
observed checks, preferably bound to the GitHub Actions app (integration ID 15368).
Do not paste workflow-qualified UI labels into the API context field. Keep
strict/up-to-date checks on and approvals at zero. This document is an activation
procedure, not a claim that repository settings have already been changed.

## Daily use and protected changes

Use a feature branch and PR template; choose one risk. Workflow, security, quality
baseline, compatibility, canonical ontology and policy changes require **high**
risk, a meaningful Governance changes explanation, the existing-gates checkbox,
and a new or updated ADR. Normal changes need no additional reviewer. Dependabot
PRs still pass all checks and need their PR metadata completed by the maintainer;
automatic dependency merging is not enabled.

The protection workflow runs from trusted main with read-only permissions. It
cannot be removed by merely changing PR head code. This is a review/evidence
control, not independent approval or a cryptographic guarantee against a sole
maintainer deliberately weakening controls. Requiring its check in the ruleset
is essential.

## Static-quality adoption

Install `.[dev]` and `requirements-quality.txt`, then run
`python scripts/check_quality.py --base origin/main`. Existing debt is listed in
`quality/static-baseline.json` by file, diagnostic, exact source and multiplicity;
new diagnostics fail. Baselines should shrink as debt is repaired. Regenerating
with `--record-baseline` is a protected policy change requiring an ADR, not the
routine response to failures. Touched/new Python files must pass Ruff formatting.
Three reviewed parameterized-SQL false positives are recorded in the Bandit
baseline; see ADR-0008. No global security rule or dependency CVE is suppressed.

## Compatibility evidence

Existing API/client/ontology gates continue unchanged. The additional report
compares immutable PR base SHA against head: existing OpenAPI values, Python
exports/SDK call signatures, SQLite CREATE TABLE definitions, and ontology
contracts. The check is deliberately conservative: changed enum/signature/DDL
values require migration review even when a change might be additive in practice.
It does not prove arbitrary function behavior or arbitrary hand-written SQL
migration safety.

For deliberate interface/DDL breaks, add
`compatibility/interface-migrations/<change_digest>.json` containing the exact
`base` SHA, `rationale`, and actionable `migration` instructions, and change the
package version. CI prints the digest and changes. Existing ontology migration
manifests and module versioning remain mandatory; an interface declaration cannot
override them. Reports are retained as Actions artifacts, including failed runs.

## Release qualification

Run **CEPIO Release Qualification** manually from main or push a matching `vX.Y.Z`
tag pointing to an integrated commit. It reruns existing CI and quality, builds
wheel/sdist/container, scans dependencies and container vulnerabilities, generates
Python/container CycloneDX SBOMs, checks version/notes, hashes artifacts, and
attests build provenance. Artifacts and manifest are downloadable from Actions.
No package, image, tag or GitHub Release is automatically published. Merged code,
Developer Preview qualification, and production qualification are distinct;
`production_qualified` remains false. Failed scans block qualification.

## Repository security settings

Enable Dependabot alerts/security updates, secret scanning and push protection
under Settings → Security → Advanced Security. These account/repository settings
are separate from committed workflows; verify activation in GitHub. CodeQL and
Dependabot configuration are versioned here. Do not claim secret scanning is
enabled merely because these files exist.
