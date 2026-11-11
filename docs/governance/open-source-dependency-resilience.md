# Open-source dependency resilience and admission v0.1

**Status:** Proposed implementation; effective after merge and passing required CI.
Architecture decision: [ADR-0061](../adr/ADR-0061-open-source-dependency-resilience.md).

## Doctrine

**Build to own; integrate to accelerate.** CEPIO owns canonical case/evidence records, provenance, ontology, Industry IQ methods and versions, policy/authority, Decisions, Outcomes and reproducibility. A third-party library or service may accelerate a bounded capability, but must not become the sole source of those records or acquire authority over them.

A retired upstream project must not render CEPIO Core unusable. Degradation of optional physics, visualization, semantic-enrichment or model providers must be explicit. Never silently present an alternative provider's outputs as the original model's result; abstain when no valid reference or fallback exists.

## Admission gates

Every **new strategic external capability** requires an explicit reviewed record before production adoption:

1. **Value:** problem, alternatives, benchmark, decision-quality or efficiency improvement, positive and negative acceptance tests.
2. **Ownership/license:** upstream reference, maintainer, license and notices, redistribution and customer-data constraints.
3. **Isolation:** versioned host-controlled API/adapter, tenant/source/actor authorization, canonical CEPIO records remain CEPIO-owned.
4. **Reproducibility:** exact upstream commit or package version, dependency/container locks, preserved model/data/calculation versions where relevant.
5. **Security:** dependency and license audit, supply-chain evidence, sandbox for untrusted/generated code, known-vulnerability remediation owner.
6. **Exit:** kill switch, truthful degradation/abstention, export/replay, replacement or classical reference, tested migration path.

The existing [Industry IQ Supply-Chain Trust](../industry-iq-supply-chain-v0.6.1.md) remains authoritative for signed pack admission. Existing release qualification, CodeQL, dependency auditing, container scans, SBOM/provenance and field-readiness gates also remain required. An agent or a JSON record cannot approve its own production adoption.

## What the v0.1 checker enforces

- The protected [OSS register](oss-dependency-register.json) declares **existing direct Python dependencies**, new-package approval records and strategic project classifications. `existing_baseline_not_requalified` is inventory status only, never a security waiver.
- `scripts/check_oss_dependency_resilience.py` inventories `pyproject.toml`, `requirements-quality.txt` and NVIDIA's CUDA 12/13 requirements. It fails for new unregistered package names, new dependencies without exact `==` version pins, missing admission evidence fields, untracked extras or invalid strategic capability records.
- Approval fields for newly declared direct packages include a reviewer/owner, license, security review, qualification evidence, version pin, fallback and exit plan. Review references must point to real evidence; CI checks presence/shape, not external authenticity.
- Strategic projects move through `candidate`, `evaluation`, `approved` or `retired`. The pre-existing optional `nx-cugraph` capability is designated `existing_optional`. An `approved` capability requires an existing adapter path and explicit owner, license, upstream revision, fallback, review/qualification evidence and exit plan.
- The checker runs in existing CI's `ci-contracts` lane; its deterministic JSON output is uploaded with contract evidence, and the existing aggregate `test` job already requires that lane. No new GitHub ruleset, Azure infrastructure, secrets, model inference or customer data are needed.

These checker/register/workflow paths are governed protected changes. Modifications require HIGH-risk review, an ADR, and IP/publication attestation. Do **not** put new packages directly into the historical baseline to bypass qualification.

## Limits

This is **not a transitive SBOM**, full source-import analysis, license determination, upstream release monitor or field-readiness certification. It does not discover vendored assets, runtime-downloaded models, indirect API providers or private CEPIO-Labs dependencies. New HTTP adapters or external components without new Python packages require manual entry and contract review. Existing security and release workflows retain responsibility for resolved dependency vulnerabilities and complete artifact provenance. Current broadly ranged packages are known debt, not retroactively requalified by this PR.

## Maintainer procedure

1. Register a proposed provider as `candidate`; evaluate it with synthetic, licensed or otherwise authorized evidence in an isolated environment. This is **not** production authorization.
2. When introducing a new direct package, record its exact version and evidence of license, vulnerability review, qualification, bounded scope and fallback. Keep reproducible build/SBOM/lock evidence under existing release qualification.
3. Test normal and adversarial paths, including missing provider, invalid output, stale evidence, wrong tenant/actor, unauthorized records, model/version drift, replay, fail-safe abstention and the replacement path.
4. Before promotion, check upstream support, maintenance cost, CVEs, licensing and whether CEPIO can export/replay its own decision history without the provider. Revisit these factors periodically; pause unsafe components rather than silently accepting risk.
5. When upstream support is withdrawn, mark the provider retired/unqualified, disable the host adapter, preserve historical records, and validate any replacement independently.

## Initial classifications

NVIDIA nx-cugraph is an **existing optional integration** with a NetworkX CPU fallback, not a new production qualification. NVIDIA Auto Ontology is **development-only**; live source use and decision uplift remain unqualified. NVIDIA PhysicsNeMo and Microsoft Data Formulator are **candidate projects** only. Nothing in this register installs or deploys them.

## Rollback and product claims

The PR can be reverted without a runtime database migration. It adds governance and CI evidence only; it does not authorize new releases, tenants, model calls or infrastructure. No maturity score, safety certification, production-ready status or external project qualification changes.
