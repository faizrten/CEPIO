# ADR-0046: Core-Only Domain Gate Qualification

Status: Proposed — governance review required
Date: 2026-10-26
Risk: HIGH (protected workflow)

## Context

The Domain Onboarding workflow triggers on shared Capability Registry code, but requires exactly one changed domain-pack manifest. Core-only changes have no legitimate onboarding target. Inventing an unrelated manifest or disabling the workflow would weaken governance.

## Decision

For pull requests without a changed domain manifest, permit a separate qualification path ONLY when every changed file belongs to a narrow, explicit Core-contract, matching-test, documentation or this workflow allowlist. This path runs the frozen Drilling/Refinery cross-domain regression with 100% survival and the existing Capability Registry, Compounding, Memory and Retrieval contract tests. Include Sovereignty tests when present. It does not run domain release or promotion.

For actual domain onboarding, require exactly one changed manifest and retain all existing onboarding, persona, promotion, human review and release controls. Changes outside the allowlist without a manifest, or changes to multiple manifests, are blocked. Manual runs still require an explicit manifest.

## Qualification

Run the modified workflow on a PR, ensure the negative routing assumptions are reviewed, and require the normal CI, Governance, CodeQL and Quality gates. No new privileges, infrastructure, spend or release claims. This is not customer sovereignty qualification. Do not merge without successful review and required checks.
