# CEPIO Environment A — Azure DEV

Environment A establishes the first progressive deployment path:

```text
LOCAL -> GitHub CI -> ACR -> Azure App Service DEV
```

It is intentionally non-production and must use synthetic or non-sensitive data only.

## Current persistence boundary

CEPIO v0.4's reference runtime supports `memory://` and `sqlite:///...`. PostgreSQL is not yet a supported repository adapter. Azure DEV therefore uses persistent App Service storage at:

```text
CEPIO_DB_URL=sqlite:////home/data/cepio.db
```

Do not point the current runtime at PostgreSQL until a production repository adapter is implemented and qualified.

## Azure resources

The Bicep template at `deploy/environment-a/main.bicep` creates:

- Azure Container Registry Basic, admin credentials disabled;
- Linux App Service Plan B1;
- Linux App Service with system-assigned managed identity;
- `AcrPull` assignment from the web app identity to ACR;
- Log Analytics workspace;
- workspace-based Application Insights.

The App Service uses managed identity for ACR image pulls and persistent `/home` storage for the DEV SQLite database.

## GitHub environment

Create a GitHub Environment named `dev`.

Configure the following **environment secrets**:

| Secret | Purpose |
|---|---|
| `AZURE_CLIENT_ID` | Client ID of the Entra application or user-assigned identity trusted by GitHub OIDC |
| `AZURE_TENANT_ID` | Azure tenant ID for GitHub OIDC |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription containing `rg-cepio-dev` |
| `CEPIO_ENTRA_TENANT_ID` | Tenant accepted by the CEPIO API |
| `CEPIO_ENTRA_AUDIENCE` | Audience / Application ID URI accepted by the CEPIO API |

Configure these **environment variables**:

| Variable | Example | Purpose |
|---|---|---|
| `AZURE_DEV_ENABLED` | `false` initially, then `true` | Enables automatic `main -> DEV` deployment after bootstrap |
| `AZURE_LOCATION` | `northeurope` | Resource-group/resource location |
| `AZURE_RESOURCE_SUFFIX` | `fs01` | Globally unique lowercase suffix for ACR/app names |
| `CEPIO_PROFILES` | `satorp` | Optional comma-separated profile list |

Keep `AZURE_DEV_ENABLED=false` until the Azure federated identity and all DEV secrets/variables are configured. Manual `workflow_dispatch` remains available for the first controlled deployment. After a successful first deployment, set `AZURE_DEV_ENABLED=true` to activate automatic deployment for qualifying changes merged to `main`.

## GitHub OIDC trust

The Azure deployment identity must have a federated credential trusting this repository and GitHub environment.

For a GitHub Environment named `dev`, use the subject:

```text
repo:faizrten/CEPIO:environment:dev
```

The deployment identity needs only the Azure permissions required to create/update the Environment A resource group and push images. During bootstrap, assigning `Contributor` on `rg-cepio-dev` plus `AcrPush` on the created registry is sufficient; reduce scope further once the deployment stabilizes.

No Azure client secret is required by the workflow.

## Deployment workflow

`.github/workflows/deploy-dev.yml` supports:

- manual `workflow_dispatch` for bootstrap and controlled runs;
- qualifying changes merged to `main` when `AZURE_DEV_ENABLED=true`.

Execution order:

```text
full CEPIO CI
  -> Azure OIDC login
  -> Bicep provision/update
  -> ACR login
  -> docker build
  -> push :<git-sha> and :dev
  -> App Service -> immutable :<git-sha>
  -> restart
  -> /api/v1/health smoke test
```

The immutable Git SHA, not `latest`, is the deployed runtime identity.

## Safety boundary

Environment A allows:

- synthetic datasets;
- ontology and semantic-runtime testing;
- REST/MCP testing;
- read-only DEV integrations;
- agent experimentation.

Environment A does not authorize:

- production customer data;
- production system credentials;
- OT/control commands;
- production SAP/EAM writes;
- production SLA claims.

## First deployment

1. Create the GitHub `dev` environment.
2. Set `AZURE_DEV_ENABLED=false`.
3. Configure the remaining secrets/variables above.
4. Configure the Azure federated identity credential for `repo:faizrten/CEPIO:environment:dev`.
5. Grant the deployment identity permission to create/update resources in `rg-cepio-dev`.
6. Merge the Environment A pull request.
7. Run **CEPIO Deploy DEV** manually for the first deployment.
8. Verify the workflow's deployment summary and `/api/v1/health` response.
9. Set `AZURE_DEV_ENABLED=true` only after the manual deployment is healthy.

## Next milestone

After Environment A is stable, implement a PostgreSQL repository adapter behind CEPIO's persistence abstraction, qualify it against the existing runtime contract, and only then replace SQLite in DEV.
