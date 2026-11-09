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


## 2026-11-09 addendum — GitHub Actions OID_API credential probe

The founder confirmed the secret name `OID_API` is already stored in CEPIO GitHub and approved a read-only cloud-side verification. To avoid unnecessary Azure grants or local workstation steps, add `scripts/cognite_oid_auth_probe.py` and a **main-only** GitHub Actions workflow for a single-asset connectivity proof.

- The workflow runs once on merge to protected `main` when its own source changes, or on explicit manual dispatch. **Never on PR head code or pull_request_target.** Only the probe step can read `secrets.OID_API`.
- The probe transmits the secret solely to the documented Cognite OID OAuth token endpoint for an explicitly bounded client-credentials attempt. Only if the OAuth token grant is denied (HTTP 400/401/403) does it attempt one Cognite API legacy `api-key` request. A successful OAuth token that lacks CDF access is a **failure**, not permission to retry an alternate credential type.
- A single `GET /api/v1/projects/publicdata/assets?limit=1` is the only CDF operation; do not print names, source records, tokens, secret values, response bodies or source identity. Disable redirects and ambient HTTP proxies; rely on standard TLS verification.
- The result states only passed/blocked, authentication mode, HTTP status codes and at most one sampled asset. No artifact upload, Azure cloud deployment, persistent token or inference. A legacy-key success signals **migration needed** before enabling the M2M Azure job; neither key nor OAuth client secret is copied into Azure by this workflow.
- A missing or scope-inaccessible GitHub secret fails safely without implying the secret is absent from the account. The operator must confirm `OID_API` is an Actions **repository** secret (not a similarly named Variable or unlinked Environment secret).

The GitHub workflow is a protected **HIGH-risk** path because it consumes a repository secret. Use the existing high-risk governance-protection gates, explicit IP publication attestations and regression tests; no relaxation of existing gates is authorized. The result is an authentication preflight only, not a live industrial-data M0 inventory or proof of judgment uplift.


## 2026-11-09 addendum — first source inventory and guarded GitHub-to-Key-Vault handoff

The founder confirmed a valid `OID_API` Actions repository secret and approved advancing cloud M0. A trusted-main read-only GitHub probe already proved OAuth client credentials and read access to one Cognite `publicdata` asset; it did **not** establish compressor asset scope, a frozen time-series history, or a source-qualified Azure job.

This incremental decision splits the next work into three **independent** tasks, rather than silently granting broad Azure permissions or moving the secret on a PR head:

1. **Read-only real M0 source inventory** — A protected-main GitHub Actions workflow `cognite-oid-m0-inventory.yml` consumes `OID_API` for bounded Cognite SDK list/search/retrieve metadata; it emits only sanitized counts/verdict and a seven-day public-OID metadata JSON artifact for reproducible review. No Azure identity is required for this task; GitHub is temporary cloud compute, not the final CEPIO product runtime.
2. **Read-only Azure landing-zone visibility** — A separate `cognite-oid-azure-readiness.yml` job attempts four GET-only lookups for previously documented `cepio-labs-rg`, ACA environment, ACR and Key Vault, using the existing CEPIO `azure-demo` environment's federated Azure OIDC identity. This does not establish resource IAM grants, Cognite job identity, Blob container rights or M0 live success. A failed lookup means *access not verified*, not resource absence.
3. **Optional secret handoff** — `cognite-oid-secret-handoff.yml` is **workflow_dispatch only** on reviewed current `main` in the protected `cognite-m0` GitHub environment. It requires both `M0_AUTH_APPROVED=true` and `M0_HANDOFF_APPROVED=true`, checks the exact existing Key Vault name/RG and validates `OID_API` with a one-record source read. On explicit operator approval, it writes a new dedicated secret using Azure CLI `--file` from a mode-0600 temporary file under Linux tmpfs; secret value never appears as an argument/log or in a build artifact. The command refuses silent rotation of an existing secret. It publishes only the non-secret, *versioned URI* for subsequent manual configuration. It neither provisions nor starts the Azure job.

**High-risk governance impact:** Two new GitHub workflows operate with deployment/Azure OIDC or read an existing repository secret and one workflow is capable of a Key Vault secret *write*. No write is invoked on PR, push or default startup. The exact Azure identity permissions must be separately verified, and all existing branch/ruleset/CodeQL/IP/quality/coverage gates remain in force. No protected Labs implementation or customer data is copied into CEPIO. After source inventory and Azure readiness are verified, the separate existing M0 job workflow `cognite-oid-m0-cloud.yml` remains the only approved mechanism for plan/deploy/run.

The Azure secret handoff workflow may be **blocked**, because `cognite-m0` GitHub Environment OIDC, permissions and the private Blob destination have not yet been live-qualified. An access-blocked or not-run handoff is a legitimate result; do not substitute unapproved personal credentials or broaden tenant permissions to force success.

**Rollback:** Leave handoff approval false/clear it to prevent further operations. For a completed transfer, revoke its job identity's permission or disable the dedicated Key Vault secret through the Azure operator; do not remove or rotate other CEPIO Labs secrets. The seven-day GitHub artifact expires automatically and contains only filtered public-OID metadata, no credentials or raw historian readings.
