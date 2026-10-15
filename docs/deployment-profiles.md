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

## Health and rollout

Both profiles use `/api/v1/health` for runtime health. Deployment metadata, image tags and CEPIO package/module/profile versions should be captured by deployment automation for auditable rollout.

## Observability

CEPIO v0.4 includes the backend-neutral telemetry hooks completed in #6. Repository, policy, function and action activity can emit sanitized telemetry, and an optional OpenTelemetry adapter is available without coupling CEPIO-Core to a specific backend.

Azure Monitor/Application Insights exporter/distro configuration remains a deployment concern. See [Observability](observability.md).

## Developer Preview qualification boundary

These profiles establish a **reproducible Microsoft-hosted reference architecture** and portable runtime image. v0.4 does not claim that a specific live customer environment has been deployed or that SQLite satisfies production HA/scale requirements. See [Developer Preview](developer-preview.md) and [RELEASE.md](../RELEASE.md) for the release boundary.
