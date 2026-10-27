# ADR-0048: Founder-only auto-merge admission with existing GitHub checks

Status: Proposed until qualification and merge

## Decision

Keep GitHub Actions and the existing CEPIO Core `main` ruleset. Add a trusted default-branch `workflow_run` admission job triggered by a successful **CEPIO CI** pull-request run. It may **enable GitHub's native auto-merge**, but it is prohibited from calling the merge API, approving reviews, bypassing branch protection, or changing required checks. It has `contents: read` and `pull-requests: write`, no checkout, no secrets, and no infrastructure permissions. The native merge is delayed until all existing required reviews/status checks and strict branch freshness rules are satisfied.

The admission service is intentionally limited to PRs both *authored by* the sole founder (`faizrten`) and *sourced from* `faizrten/CEPIO`, with an unchanged SHA matching the successful PR CI run. It rejects forks, drafts, deletions, renames, binary changes, mixed changes, stale runs, large diffs, unknown paths, and sensitive or foundational files. It rereads the PR immediately before admission.

- **R0 automatic:** At most three small `.md` changes (at most 150 changed lines total) strictly within the explicitly allowlisted public glossary, developer guide, reference scenarios, API examples/client guide, and developer preflight/bindings documentation. The owner selects `low` and the public-IP classification.
- **R1 owner-opted:** At most two *new* `tests/test_*.py` files (250 changed lines total), with security/governance/deployment-related test names excluded. The owner selects `medium`, confirms public-IP attestations and checks `R1 auto-merge authorized by founder` in a `## Review automation` section. Existing tests cannot be modified or deleted through this path.
- **R2/R3:** Never admitted to automatic merge; keep founder-controlled oversight and existing governance/approval boundaries.

This is deliberately narrower than the advisory R0–R3 classifier. The classifier is informational and must not authorize merges.

## Security and operational safeguards

A successful CI run alone does not authorize merge: the native GitHub auto-merge mutation leaves status checks, CodeQL, quality/coverage, publication review and all ruleset controls in force. If GitHub refuses auto-merge, the workflow logs a warning and performs no direct merge. Production deployments, cloud permissions, paid Foundry inference, spending controls and tenant data boundaries are unchanged.

The `workflow_run` trust boundary runs the reviewed default-branch workflow and **never checks out or executes the PR head**. External PRs do not qualify even if their CI succeeds. The path checks are defensive filters, not proof of document confidentiality; the founder remains accountable for confirming publication scope.

CEPIO Labs and Industry IQ Studio retain advisory risk triage only. Their private repository auto-merge settings and effective protections have not been qualified for unattended merging.

## Validation and rollback

The acceptance test runs the actual embedded policy script offline with mocked GitHub APIs, covering eligible R0/R1 and at least 14 denial cases. Normal CI, security, governance, and quality checks must pass on this PR before merging. Confirm a future eligible PR is admitted but *not* merged until required checks finish, and verify an R2/R3 PR remains manual.

To roll back, remove `.github/workflows/owner-auto-merge.yml`. GitHub auto-merge already enabled on individual PRs can be disabled manually. No repository settings need to change.
