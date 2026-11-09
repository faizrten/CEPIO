# Cognite OID M0 — Azure cloud execution runbook

**Status:** Source-only, opt-in. No Azure resource was provisioned or live Cognite source queried in this PR.

## Architecture and scope

Cognite OID publicdata → read-only manual Azure Container Apps Job → existing **private** Azure Blob container → create-only JSON evidence manifest, read-back SHA-256 qualification → future read-only CEPIO Management/Studio projection.

**This is source conformance, not a validated engineering decision.** The inventory uses bounded metadata list/search/retrieve only. No raw datapoints, P&ID file content, CDF mutations, inference, OT actions or API host registration. The job runs on demand with zero retries.

## Authentication restriction (critical)

The Cognite public OID Python/Postman app (client ID `1b90ede3-271e-401b-81a0-a4d52bea3273`) supports interactive OAuth with just the published identifiers. **Cognite has also documented a client-secret generator for OID client-credentials flows**; an appropriately generated *secret* may permit unattended cloud access using that same published app/client ID. The published identifiers **alone are not credentials**.

1. Sign in to [Cognite Hub → Open Industrial Data](https://learn.cognite.com/open-industrial-data) and look for the OID *Generate/Create client secret* option. Cognite's historical guidance says to choose **Other** for Python/Postman (not JavaScript); see [Cognite's instructions](https://hub.cognite.com/open-industrial-data-211/how-to-generate-a-client-secret-for-open-industrial-data-1226).
2. Confirm the generated secret is still supported and grants read-only `publicdata` access. This documentation is dated, and some users have reported that the widget was temporarily unavailable. If missing, contact Cognite OID support; **do not fabricate a client secret**.
3. Store the secret **directly** in an existing Azure Key Vault, retrieve its *versioned Key Vault secret URI*, and give the Container Apps job identity secret-read permission. Do not paste the secret into chat or GitHub, or leave it in plaintext shell history.
4. Only then use the Cognite-approved tenant and client ID in the cloud job. The runner still refuses any unattended access without a valid M2M secret. Credentials/permissions will be verified by Cognite at execution time.

Do not persist delegated refresh tokens or bypass the IdP. The secret must be supplied by Key Vault reference—not in GitHub Actions environment variables, Bicep parameters or repository files.

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
| `M0_COGNITE_M2M_CLIENT_ID` | Cognite-approved client ID; the published Python OID client may be used **only with Cognite-issued client secret and verified rights** |
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


## Step 0 — GitHub-hosted OID_API access preflight

Before provisioning Azure, use the existing **Actions repository secret** named `OID_API`. The `CEPIO Cognite OID_API Read-Only Probe` workflow runs automatically only when its own reviewed source is merged into `main`, and can be rerun manually from **GitHub → Actions → CEPIO Cognite OID_API Read-Only Probe → Run workflow** on `main`.

This step has no Azure provisioning or local Python requirement. It tries Cognite's documented OAuth client-credentials grant for OID (`publicdata`, cluster `api`) and then, **only if the grant is rejected**, one legacy `api-key` GET to the same project. The asset response is bounded to **one item** and never printed. GitHub logs report only the authentication method and an allowlisted status or denial code. Never put a token, key or secret into a workflow input or the chat.

**Interpretation:**

- `passed / oidc-client-credentials`: the GitHub secret is usable as an OID client secret with read permission. Next, configure it in an approved Azure Key Vault through a secure operator action. It is **not** yet available to Azure Container Apps simply because it exists in GitHub.
- `passed / legacy-api-key`: a legacy key still works for this bounded read, but is deprecated; migrate to Cognite-issued OIDC client secret before starting the existing Azure job, which requires OAuth.
- `blocked / OID_API-secret-not-visible-to-job`: it is not available as an Actions repository secret to this workflow (it may be an Environment-scoped secret or Actions variable). Check scope/name in repository Settings. No value is read from this chat.
- `blocked / oidc-and-legacy-auth-rejected-or-malformed`: retrieve HTTP codes in the log. Common causes include an expired client secret, incorrect application/grant, lack of project authorization or Cognite's rejection of deprecated keys. Do **not** turn off TLS checks or silently switch projects.

This verifies only one source read. The *separate* M0 inventory and decision replay qualification gates remain open until the appropriate Azure identity/storage pipeline is reviewed, deployed and operated successfully.
