# Cognite OID M0 — Azure cloud execution runbook

**Status:** Source-only, opt-in. No Azure resource was provisioned or live Cognite source queried in this PR.

## Architecture and scope

Cognite OID publicdata → read-only manual Azure Container Apps Job → existing **private** Azure Blob container → create-only JSON evidence manifest, read-back SHA-256 qualification → future read-only CEPIO Management/Studio projection.

**This is source conformance, not a validated engineering decision.** The inventory uses bounded metadata list/search/retrieve only. No raw datapoints, P&ID file content, CDF mutations, inference, OT actions or API host registration. The job runs on demand with zero retries.

## Authentication restriction (critical)

The Cognite public OID application (Python/Postman client ID `1b90ede3-271e-401b-81a0-a4d52bea3273`) uses an interactive OAuth flow. Its published tenant/client identifiers do not authorize unattended server access. The cloud runner rejects this client ID and the public JavaScript OID client ID as M2M.

**Before deployment**, obtain a Cognite-approved machine-to-machine client with read-only access to `publicdata`. The exact permission grant is governed by Cognite/the OID administrator. If this is unavailable, leave cloud execution blocked. Do not persist delegated refresh tokens or bypass the IdP. The M2M secret must be held in an existing Azure Key Vault and supplied via a *versioned Key Vault secret URI*; never store secret values in GitHub.

An Azure **user-assigned managed identity** (distinct from the Cognite M2M application) authenticates to Blob Storage and can read the approved Key Vault secret. Prefer a job-specific identity over expanding the CEPIO API host's privileges.

## Reuse existing Azure infrastructure

The job Bicep at `deploy/cognite-oid-m0/job.bicep` is opt-in (`authorized=false` by default). It does **not** create a resource group, identity, registry, Key Vault, Storage account or role assignment. Verify the existing non-production resource IDs and permissions. An account used for Azure Files may also support Blob Storage; a private Blob container must be provisioned/selected separately.

The job identity needs **AcrPull** on existing ACR, **Key Vault Secrets User** scoped to the specific secret, and **Storage Blob Data Contributor** scoped to the evidence container. Avoid broader scopes. The GitHub OIDC deployment identity needs appropriately scoped ARM job create/update/start plus registry build permissions. Microsoft warns that Container Apps Job start rights can enable runtime overrides and access to secrets. Grant those permissions only to trusted operators.

## GitHub Environment setup (after code review)

Workflow: `.github/workflows/cognite-oid-m0-cloud.yml`. Trigger: manual `workflow_dispatch` on reviewed, current `main` only. Use a protected GitHub Environment named `cognite-m0` with GitHub OIDC federation; verify this repo's **custom/immutable OIDC subject** rather than assuming the default.

Environment **secrets** for Azure deployment OIDC login (not Cognite secrets): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

Environment **variables**:

| Variable | Value |
| --- | --- |
| `M0_RESOURCE_GROUP` | Existing non-production RG |
| `M0_CONTAINER_APPS_ENVIRONMENT_ID` | Existing ACA managed environment resource ID |
| `M0_IDENTITY_RESOURCE_ID` / `M0_IDENTITY_CLIENT_ID` | Approved job user-assigned identity |
| `M0_ACR_NAME` / `M0_ACR_SERVER` | Existing ACR name / login server |
| `M0_BLOB_ACCOUNT_URL` | `https://<account>.blob.core.windows.net` |
| `M0_BLOB_CONTAINER` | Existing private Blob container |
| `M0_COGNITE_M2M_TENANT_ID` | Cognite-approved M2M authority tenant |
| `M0_COGNITE_M2M_CLIENT_ID` | Cognite-approved M2M client (NOT the published public OID app) |
| `M0_COGNITE_SECRET_KEYVAULT_URI` | Versioned Key Vault secret URL (not secret value) |
| `M0_AUTH_APPROVED` | Literal `true` required before deploy/run; leave unset while unqualified |

**Do not invent** resource names or client IDs to satisfy workflow preflight.

## Manual execution

1. Review/merge CEPIO PR only if Governance, CI, CodeQL, Quality and IP checks are green. **Merge does not deploy.**
2. Configure the protected `cognite-m0` Environment and approved M2M/access resources.
3. Open **GitHub → Actions → CEPIO Cognite OID M0 Cloud → Run workflow → plan**. This uses Azure `what-if`; it does not provision.
4. Inspect plan and verify scope/permissions, then set `M0_AUTH_APPROVED=true` and dispatch **deploy**. It builds an image tagged with the Git commit, provisions only the manual job, and does **not** start it.
5. Dispatch **run** explicitly. In **Azure → Container Apps Jobs → cepio-cognite-oid-m0 → Executions**, verify successful completion and locate the manifest in Blob Storage beneath `cepio/cognite-oid/m0/publicdata/YYYY/MM/DD/<run-id>.json`.
6. Check the logged manifest SHA-256 against the stored blob digest. Review source metadata in the report before declaring M0 live qualified.

A successful job or source conformance alone does not establish Valhall compressor readiness. Report distinct outcomes: `blocked`, `needs-domain-review` or `source-qualified-pending-engineering-review`. Verify actual compressor asset coverage, related time series, engineering units, timestamp semantics and maintenance event connections separately.

## Product end-state qualification

A later Studio increment should expose the latest **authorized** cloud receipt via CEPIO's read-only Management Contract and Studio server-side BFF. Do not expose direct Blob credentials or raw source files to the browser, and do not mark a binding 'ready' from a configuration record alone.

M1 will freeze bounded historian history with source hashes, signal units and time windows; M2 will compare LLM-only, CEPIO-only and LLM+CEPIO on equivalent evidence; M3 will deliver reproducible decision-review and calibrated what-if experiences in Studio.

## References

- Azure Container Apps Jobs: https://learn.microsoft.com/en-us/azure/container-apps/jobs
- Cognite Python SDK OAuth: https://cognite-sdk-python.readthedocs-hosted.com/en/stable/cognite_client.html
- Azure Blob and managed identity: https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python
- CEPIO Binding Contract: `docs/developer/platform-bindings.md`
- CEPIO Reliability Lighthouse: `docs/reliability-agent-lighthouse.md`
