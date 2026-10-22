# ADR-0036 — Proprietary Core and Intentional Public Interfaces

**Status:** Accepted for implementation
**Date:** 2026-10-22
**Classification:** PUBLIC governance decision

## Context

CEPIO currently publishes a complete working source repository even though it includes differentiating industrial runtime, qualification and domain assets. The private CEPIO-Labs repository already establishes an IP register, a publication-candidate review and a public-interface / protected-intelligence boundary. The full source publication is wider than this boundary.

## Decision

1. Treat the full `faizrten/CEPIO` source repository as proprietary and change its GitHub visibility to **private** using the repository owner's administrative settings.
2. Until that change takes effect, fail the required `governance-protection` PR check for modified or newly added implementation, domain intelligence, qualification and customer-profile paths. Deletions of already-public material may proceed as containment.
3. After the privacy change, keep normal main-branch, CI, CodeQL, quality and operational-governance controls. The publication embargo automatically ceases to block internal PRs when the GitHub event reports the repository is private.
4. Publish deliberate API, SDK, MCP, schema, documentation and sanitized-example extracts via a separate public developer surface. Do not copy the full private implementation to that surface.
5. Keep customer-specific proprietary information in customer-controlled boundaries and protected industrial intelligence in private CEPIO / CEPIO-Labs, with classification and provenance controls.

## Safety and deployment compatibility

This ADR does not remove or alter deployed API endpoints, tokens, Azure resources, OIDC trust, CI artifacts, build recipes, source code or release baselines. Repository visibility does not itself prove that deployments or external consumers continue working; verify Actions, package access, Azure OIDC, build dependencies and anonymous application endpoints after the visibility change.

## Disclosure caveat

The historical public baseline remains a prior disclosure. Public forks, clones, caches, releases and package distributions may survive the visibility change. Copyright, licensing, employee invention assignment and patent/trade-secret protection must be reviewed separately.

## Validation

- Required status check already includes `governance-protection`.
- Governance check inspects PR filenames from the trusted base workflow, and never executes untrusted PR code.
- Publish-only PR changes remain subject to explicit IP classification and existing branch rules.
- Confirm private visibility separately using GitHub repository metadata.
