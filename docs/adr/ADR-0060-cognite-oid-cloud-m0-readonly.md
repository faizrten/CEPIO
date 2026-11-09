# ADR-0060 — Cognite OID M0 on-demand Azure evidence inventory

**Status:** Proposed for PR #351
**Date:** 2026-11-09
**Risk:** HIGH — changes to cloud GitHub workflows and infrastructure as code
**Publication:** PUBLIC — sanitized provider binding and cloud orchestration; protected industry intelligence remains private

## Context

CEPIO must prove its ability to work over real industrial evidence from Cognite Open Industrial Data while preserving the core north star of decision reproducibility. M0 is an inventory and source-conformance qualification, not an inference, process-history reconstruction or operational decision.

The end-user wants an Azure-native experience rather than local Python scripts. Cognite publishes project identifiers and a delegated OAuth application; public tenant/client IDs alone do not authorize unattended server access. Cognite also documents generating a separate client secret for client-credentials use, subject to current OID portal support and actual access permissions.

## Decision

1. Run a **manual** Azure Container Apps Job, not a long-running API-host process. Job has one parallel replica and zero retries; no schedule or automatic deployment.
2. Read only bounded Cognite OID asset, time-series, event and file **metadata** using list/search/retrieve. No raw datapoints, file download, source-system mutation, paid LLM inference or OT actions at M0.
3. Preserve provider-neutral Binding Contract v0.1, project-scoped Cognite numeric IDs, metadata revisions, source references and lineage. Do not copy Cognite's industrial graph wholesale into CEPIO. Last-update metadata timestamps are not a historian snapshot or evidence of a physical event.
4. Use an explicitly approved Cognite OAuth client-credentials identity and a **valid separately generated secret** held in an existing Azure Key Vault. Cognite's published OID client ID may work with an issued secret; the ID itself is never a credential. Never persist delegated refresh tokens in the job.
5. Use a separate approved **user-assigned managed identity** for Azure Blob, existing ACR pull and specific Key Vault secret access. No new Azure identities, role grants, registries, Key Vaults, storage accounts or containers are created in this PR.
6. Persist each capped manifest in an existing private Blob container with a unique run-specific path, create-only upload, read-back SHA-256 verification, and no false success on unknown/failed outcomes.
7. Use the protected GitHub Environment `cognite-m0`, immutable reviewed commit image and a manual workflow with explicit `plan`, `deploy` and `run` operations. Deployment/operation require separate approval and non-production RBAC. Source merge never deploys Azure.
8. Provide a no-credentials/no-deployment GitHub Bicep compilation workflow. Retain all existing trusted-base governance-protection, Quality, CI, CodeQL, compatibility and IP protections.

## Protected workflow change and risk analysis

Two workflow paths under `.github/workflows/` add a deliberately gated cloud provisioning/control-plane surface and a build-only infrastructure validator. Even though a read-only Cognite connector is the initial consumer, the deployment workflow can use an Azure OIDC deployment identity. That potential for Azure mutation and secret-reference configuration makes this a **high-risk** source change. A protected environment and least-privilege identity are required for any future live run; no secrets enter GitHub source, logs or workflow variables.

## Alternatives

- Local interactive Python was rejected as the normal end-user path (still available for troubleshooting).
- Adding Cognite ingestion to CEPIO's always-on API host would unnecessarily expand host IAM and resource responsibilities.
- Scheduled ingestion creates ongoing cost and trust scope before proving real data usefulness.
- Reusing a delegated refresh token is not an appropriate unattended identity scheme.
- Direct Studio browser-to-Blob access bypasses CEPIO's authenticated Management BFF.
- Copying full source data and provider semantics into Core undermines provider portability.

## IP / publication review

This is a sanitized public interoperability example: only metadata binding, deterministic qualification checks, source-scoped cloud orchestration and documentation. No proprietary Industry IQ diagnostics, private evaluation corpus, protected scenario logic, customer mappings, data, credentials or operational thresholds are in this PR. Industrial judgment methods remain private and customer-specific data remains customer-controlled.

## Validation

- Offline fake-CDF/fake-Blob regression tests cover read-only interfaces, denied identity/project, version provenance, unique manifest, negative outcomes, create-only write and hash readback.
- Existing CEPIO CI, architecture, quality/coverage, CodeQL and governance checks must all remain required and pass.
- Added Bicep compilation job has no Azure login and never provisions cloud resources.
- Manual Azure `plan` must show only the expected ACA Job change before any approved `deploy`.
- Cloud M0 requires verified Cognite OAuth client-secret grant, matching private Blob receipt, actual compressor assets and review of relevant time series / maintenance metadata. Successful CI is **not** evidence of live Cognite access.
- Subsequent M1/M2 will use frozen historian evidence and blind comparative assessment to establish engineering judgment uplift.

## Rollout and rollback

This ADR authorizes source-only work, **not** customer-tenant deployment, resource provisioning or operational control. The user-controlled Azure operator must configure the existing resources and approve a manual deployment. Removing the manual job disables new executions; secret access and Blob retention remain under the existing platform owner's governance.

**Existing gates remain enforced.** There is no lowering of coverage thresholds, risk checks, public IP boundaries, Azure authorization or runtime data controls.
