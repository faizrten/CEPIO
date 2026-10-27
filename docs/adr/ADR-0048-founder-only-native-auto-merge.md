# ADR-0048: Founder-only R0/R1 merge qualification and safe activation boundary

Status: Proposed until required checks pass

## Decision

Keep GitHub Actions and the existing CEPIO Core main ruleset. Introduce a trusted, default-branch `workflow_run` that **qualifies** exceptionally low-risk founder-authored pull requests after a successful CEPIO CI run. The workflow is **read-only** (`contents: read`, `pull-requests: read`), has no checkout, no deployment credentials, and no merge API mutation. GitHub's native auto-merge remains available to the founder in the repository interface and still enforces all required security, quality, coverage, code-scanning and governance checks.

The workflow validates that the PR belongs to `faizrten/CEPIO`, was authored by `faizrten`, is not a draft, and that its head SHA exactly matches the completed PR CI run. It reads the file list from the GitHub API, rejects stale results and rechecks the PR before returning a qualification.

- **R0:** At most three small, explicitly allowlisted documentation files and 150 changed lines, with a checked low-risk and PUBLIC IP classification.
- **R1:** At most two *new* `tests/test_*.py` files totaling 250 changed lines, excluding security, governance, migration, deployment and other protected tests. Requires medium risk, explicit `R1 auto-merge authorized by founder` opt-in and all existing public-IP attestations.
- **R2/R3:** Never qualified by this narrower policy; they remain manually controlled under existing gates.

Rename, deletion, binary, excessive, unknown, mixed or externally authored PRs are denied. Qualifications are advisory and do not grant approval or bypass any GitHub rule.

## Why unattended auto-merge is not yet activated

We evaluated enabling `enablePullRequestAutoMerge` through the standard GitHub Actions `GITHUB_TOKEN`. Current GitHub documentation and community examples indicate this can require both `contents: write` and `pull-requests: write`. More importantly, operations performed with the default Actions token can suppress subsequent workflow triggers, notably `push` CI after merges. Unattended merging without proving the post-merge verification path would weaken CEPIO's release assurance.

Therefore, this milestone deliberately does not grant repository write scopes or activate the merge mutation. Before enabling unattended merge, use an appropriately scoped GitHub App installation identity, verify that merges it initiates trigger the expected post-merge workflows, and run a live R0 negative/positive test under the unchanged ruleset. Never use direct merge, administrative bypass, or a PAT copied into code.

## Tests and rollback

Credential-free Node.js acceptance tests execute the embedded admission logic with mocked GitHub APIs for eligible R0/R1 cases and denied unauthorized, forked, stale, protected, renamed, binary, changed-head and missing-opt-in cases. Full GitHub CI and existing main protection must pass.

Rollback: remove `.github/workflows/owner-auto-merge.yml`. This has no effect on production deployment, model inference, cloud roles, repository rulesets, or existing GitHub auto-merge settings. CEPIO Labs and Industry IQ Studio retain advisory risk triage because their private repository merge protections and auto-merge settings have not yet been qualified.
