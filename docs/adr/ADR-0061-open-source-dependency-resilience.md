# ADR-0061 — Replaceable open-source dependencies and a fail-closed admission gate

- **Status:** Proposed; pending required CI and governance review
- **Date:** 2026-11-11
- **Risk:** HIGH — changes to protected CI, security/governance checker and dependency register
- **Publication:** PUBLIC — provider-neutral controls and sanitized metadata; no private Industry IQ or customer material

## Context

CEPIO benefits from Microsoft and NVIDIA open-source tools, but upstream repos may be deprecated, stop patching vulnerabilities, or break compatibility. Canonical case evidence and decision histories must survive their retirement. Current [Industry IQ supply-chain trust](../industry-iq-supply-chain-v0.6.1.md) already governs signed external packs, while quality/release workflows produce dependency scans, SBOM and provenance. No parallel pack-admission control should be built.

## Decision

1. Preserve CEPIO-owned data, evidence, methods, decisions, authority and audit. Third-party analytics/physics/visualization and agent libraries use replaceable, versioned, host-controlled adapters. If a provider is unavailable, fail explicitly or use a qualified, attributed fallback; never invent equivalent physical conclusions.
2. Introduce a reviewed, machine-readable register identifying historical direct Python declarations (without claiming qualification), **new package approvals**, and strategic OSS maturity. New direct packages require exact version pins, an owner, license/security evidence, qualification, fallback and exit plan. An approved strategic provider needs an adapter path and reviewed metadata.
3. Run a deterministic stdlib-only checker in the existing `ci-contracts` lane; upload an inventory JSON artifact and compare the grandfathered baseline against the immutable PR/push base commit after first-adoption bootstrap. The existing `test` CI aggregate includes that lane. Do not add a new bypass actor, ruleset, secrets, external infrastructure or inference.
4. Keep human review for transitive, vendored and runtime-downloaded software, source integrations, upstream health, legal terms, customer/tenant boundaries and actual production qualification.
5. Record current statuses truthfully: nx-cugraph is existing optional; NVIDIA Auto Ontology remains development-only; PhysicsNeMo and Data Formulator are candidates, not installed CEPIO dependencies.

## Trade-offs

Benefits: explicit reversibility, inventory traceability and earlier failures on unreviewed package introductions. Costs: maintainer effort, exact version management and ongoing retirement monitoring. A fork of an abandoned dependency can remain an option, but requires maintenance and security ownership.

Rejected: forking a third-party app as CEPIO's system of record, making external runtimes indispensable to Core, automatic third-party promotion, automatic production installation, or replacing the existing supply-chain security framework.

## Validation required

`python scripts/check_oss_dependency_resilience.py --inventory-out oss-direct-dependency-inventory.json` and `pytest -q tests/test_oss_dependency_resilience.py` must pass. Negative tests reject unregistered dependencies, loose new pins, missing security-review evidence, untracked optional groups and insufficiently qualified approved providers. Hosted CI, compatibility, CodeQL, governance-protection and existing drilling/refinery regression checks remain prerequisites to merge.

## Rollback and claims

Revert the governance increment through an approved PR if necessary; no persistent data or runtime API is changed. No production-readiness, field validation, customer deployment, release gate or governed scorecard increase is claimed.
