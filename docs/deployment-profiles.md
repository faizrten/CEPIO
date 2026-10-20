# CEPIO v0.4 Reference Deployment Profiles

CEPIO uses one portable runtime image and keeps hosting concerns outside CEPIO ontology semantics.

## Runtime image

Build from the repository root:

```bash
docker build -t cepio:v0.4-dev-preview .
```

The image starts:

```text
uvicorn cepio.public_api:app --host 0.0.0.0 --port $PORT
```

Required production configuration includes `CEPIO_ENVIRONMENT=production`, an explicit `CEPIO_DB_URL`, and Entra authentication settings.

CI builds the image and starts it independently before probing `/api/v1/health` as part of the Developer Preview release gate.

## App Service profile

`deploy/appservice/main.bicep` provisions a Linux Premium App Service with:

- system-assigned managed identity;
- HTTPS-only transport;
- `/api/v1/health` health check;
- Entra-backed CEPIO runtime configuration;
- App Service container storage explicitly enabled for persistent `/home/data` reference storage;
- one CEPIO container image contract shared with AKS.

Example:

```bash
az deployment group create \
  --resource-group <rg> \
  --template-file deploy/appservice/main.bicep \
  --parameters appName=<name> containerImage=<registry/image:tag> tenantId=<tenant> apiAudience=<audience>
```

The reference profile sets `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` because the SQLite reference URL is `sqlite:////home/data/cepio.db`.

VNet integration, private endpoints, ACR pull roles, Key Vault access, Application Insights connection and deployment slots are environment-level bindings and should be added by the target platform landing zone rather than CEPIO-Core.

For a private Azure Container Registry image, grant the app's system-assigned
identity `AcrPull` on the registry and enable `acrUseManagedIdentityCreds` in the
app's site configuration. Do not enable registry admin credentials. Cloud builds
can use `az acr build` when Docker is unavailable locally; review the build
context before uploading it and exclude credentials through `.dockerignore`.

The reference plan uses one paid P1v3 instance. Keep it at one instance with
SQLite and do not enable autoscaling. The existing `cepio-demo-31d48` deployment
uses `sqlite:////home/cepio.db`, directly in the persistent `/home` mount; this
does not change the template's `/home/data/cepio.db` storage contract. When
using the template default, provision a writable `/home/data` directory before
runtime startup. Confirm `/api/v1/health` returns HTTP 200 and an unauthenticated
request to `/api/v1/objects` returns HTTP 401 after deployment.

## GitHub Actions deployment

`.github/workflows/deploy-azure.yml` deploys the existing Azure demo resources
after **CEPIO CI** succeeds for a push to `main` in this repository. Pull-request,
fork, failed, and non-main CI runs cannot enter the deployment job. The workflow
checks out the trusted `refs/heads/main` branch and verifies that both its local
SHA and the current remote main SHA match the successful CI commit before Azure
login. It rejects a superseded commit after approval, builds in ACR with a
unique commit/run/attempt tag, and configures
App Service with the resulting immutable image digest. Deployment jobs are
serialized and do not cancel an active rollout.

This targets the already provisioned `cepio-demo-rg` app/registry, not
[Environment A](environment-a-azure-dev.md). The separate
`.github/workflows/deploy-dev.yml` provisions Environment A infrastructure
and remains unchanged. Do not enable its `AZURE_DEV_ENABLED` setting or reuse
its `dev` identity/environment to operate this existing demo. The demo workflow
cannot provision resources and has no resource-group-wide permissions.

### One-time identity and GitHub environment setup

Use a dedicated Entra application/service principal, separate from the CEPIO
API identity. Do not create client secrets or give it a CEPIO domain role.
Configure a federated credential with:

| Field | Value |
|---|---|
| Issuer | `https://token.actions.githubusercontent.com` |
| Subject | `repo:faizrten@102391346/CEPIO@1418774983:environment:azure-demo` |
| Audience | `api://AzureADTokenExchange` |

This repository enables GitHub's immutable OIDC subject format. Discover the
configured prefix rather than assuming a name-only subject:

```text
GET /repos/faizrten/CEPIO/actions/oidc/customization/sub
```

For this repository, the response has `use_immutable_subject: true` and
`sub_claim_prefix: repo:faizrten@102391346/CEPIO@1418774983`. Append
`:environment:azure-demo` exactly, including case. Other repositories may use
the legacy name-only format or custom subject claims; use their configured
prefix and verify the actual assertion subject in the Azure login output.
Keep the issuer and audience exact as well.

An `AADSTS700213` failure means Entra could not match the asserted subject to
the federated credential. Update the existing credential to the verified exact
subject, read it back, and rerun the failed job after propagation. The retry
requires a fresh human environment approval. Do not add wildcard trust, disable
immutable subjects, or bypass approval to resolve an identity mismatch.

Grant this deployment principal **Contributor** only on the target ACR registry
for cloud builds and **Website Contributor** only on the target web app.
It does not need subscription-wide access or permission to assign roles.
The web app's separate managed identity retains its `AcrPull` assignment.

In repository **Settings > Environments**, create `azure-demo`, require a human
reviewer, and allow deployments only from the `main` branch (not tags). For
this single-maintainer demo, the maintainer may approve their own deployment;
teams should prohibit self-review and assign an independent reviewer. Keep
administrative bypass disabled where GitHub supports it.

Set these environment **variables**, not secrets:

| Variable | Purpose / demo value |
|---|---|
| `AZURE_CLIENT_ID` | Dedicated deployment application's client ID |
| `AZURE_TENANT_ID` | Target Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | `cepio-demo-rg` |
| `AZURE_WEBAPP_NAME` | `cepio-demo-31d48` |
| `AZURE_CONTAINER_REGISTRY` | `cepiodemo31d48` |

Environment protection is a server-side GitHub setting, not something the
workflow file creates. GitHub plan/repository visibility can affect which
protection features are available. Do not relax the OIDC subject to a wildcard
or enable privileged pull-request execution to work around missing approvals.

### Operating the deployment

1. Submit changes through a pull request and wait for CEPIO CI to pass.
2. Merge to `main`; the main push runs CI again.
3. Open **Actions > Deploy CEPIO to Azure** and approve the pending `azure-demo`
   deployment after checking the commit.
4. Check the run summary for the commit, image digest, health URL, and HTTP 401
   anonymous-read check. Health must return JSON with `status: ok`.

The workflow must first be merged onto the default branch before `workflow_run`
can trigger it. If a deployment is rejected as superseded, approve the deployment
for the latest successful main CI run instead. A failed build/rollout/check fails
the job explicitly; there is no automatic rollback. Inspect the failure before
redeploying a known-good digest or reverting via a new reviewed main commit.

This pipeline updates an existing app; it does not provision infrastructure,
change Entra user roles, alter storage settings, seed data, or scale the app.
Restarts can briefly interrupt the single-instance SQLite demo. Never enable
multi-instance rollout slots/autoscaling with this reference persistence.
Health and anonymous rejection are smoke checks, not proof of full functional
correctness or of the running container's commit identity.

Validate the local deployment contracts with:

```text
python scripts/validate_deployment_profiles.py
python -m pytest -q tests/test_deployment_workflow.py
```

Existing CEPIO CI runs both the deployment profile validator and the pytest
suite. Ontology semantics and migration contracts are unchanged by deployment.

## AKS profile

`deploy/aks/cepio.yaml` provides a reference namespace, service account, persistent volume, deployment, service and probes.

The service account is prepared for Microsoft Entra Workload Identity using the `azure.workload.identity/client-id` annotation. Replace the placeholders before applying the manifest.

```bash
kubectl apply -f deploy/aks/cepio.yaml
```

Private ingress, network policy, Key Vault CSI, Azure Policy, Azure Monitor and autoscaling should be composed by the target AKS platform profile.

## Persistence and scaling boundary

The repository currently ships an in-memory and SQLite reference repository. SQLite is intentionally a **single-writer reference deployment** and must not be treated as a horizontally scalable production data plane.

Therefore:

- App Service reference deployments should remain single active writer when using SQLite;
- the provided AKS SQLite manifest uses `replicas: 1` and `ReadWriteOnce` storage;
- horizontal runtime autoscaling is enabled only after a production repository adapter supports shared/partitioned persistence and the required consistency contract.

This is deliberate: hosting scale must not create semantic corruption.

## Identity boundary

Human/API callers continue to authenticate through Microsoft Entra and CEPIO derives actor context from validated token claims. Azure managed identity / AKS workload identity authenticates the **workload to Azure dependencies**; it does not replace CEPIO actor identity for user or agent actions.

For a dedicated Entra API registration, request v2 access tokens
(`api.requestedAccessTokenVersion: 2`) and use the API client ID as
`CEPIO_ENTRA_AUDIENCE`. Expose a delegated `access_as_user` scope and define
application roles whose values match CEPIO policy roles, such as `auditor` and
`cepio_admin`. Assign the selected role to the user on the API's enterprise
application; defining a role alone does not grant access.

For Azure CLI access, an administrator can preauthorize the Microsoft Azure CLI
client (`04b07795-8ddb-461a-bbee-02f9e1bf7b46`) for the delegated scope.
Authenticate to the correct tenant before requesting a token. In PowerShell:

```powershell
$apiClientId = '<API application client ID>'
$appUrl = 'https://<app-name>.azurewebsites.net'
$token = az account get-access-token --scope "api://$apiClientId/access_as_user" --query accessToken --output tsv
if ($LASTEXITCODE -ne 0) { throw 'Unable to acquire a CEPIO API token' }
Invoke-RestMethod "$appUrl/api/v1/objects" -Headers @{ Authorization = "Bearer $token" }
Remove-Variable token
```

Do not print, persist, or commit access tokens. Token acquisition may require a
fresh interactive sign-in or tenant administrator consent. A health check does
not verify user authorization; test a protected route with a real token as well.

## Health and rollout

Both profiles use `/api/v1/health` for runtime health. Deployment metadata, image tags and CEPIO package/module/profile versions should be captured by deployment automation for auditable rollout.

## Observability

CEPIO v0.4 includes the backend-neutral telemetry hooks completed in #6. Repository, policy, function and action activity can emit sanitized telemetry, and an optional OpenTelemetry adapter is available without coupling CEPIO-Core to a specific backend.

Azure Monitor/Application Insights exporter/distro configuration remains a deployment concern. See [Observability](observability.md).

## Developer Preview qualification boundary

These profiles establish a **reproducible Microsoft-hosted reference architecture** and portable runtime image. v0.4 does not claim that a specific live customer environment has been deployed or that SQLite satisfies production HA/scale requirements. See [Developer Preview](developer-preview.md) and [RELEASE.md](../RELEASE.md) for the release boundary.
