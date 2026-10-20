# Deployment and Operations

## Current state

CEPIO can be run locally and tested cloud-independently. The current roadmap focus is formal Microsoft-native deployment profiles.

## Local/reference deployment

Requirements include Python 3.11+.

```bash
git clone https://github.com/faizrten/CEPIO.git
cd CEPIO
python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python examples/demo.py
```

Start the API:

```bash
uvicorn cepio.api:app --reload
```

API documentation is available from the FastAPI OpenAPI UI during local execution.

## Persistence

Reference persistence can use SQLite:

```python
from cepio.bootstrap import build_runtime
runtime = build_runtime(sqlite_path="cepio.db")
```

SQLite is a reference implementation, not the target enterprise-scale runtime.

## App Service profile — roadmap/current priority

The [reference App Service template](../../deploy/appservice/main.bicep) hosts
the REST API with Entra authentication and one paid P1v3 instance. It explicitly
enables persistent App Service storage and uses `/home/data/cepio.db` for
reference SQLite data. The existing Azure demo uses `/home/cepio.db` on that
same persistent mount without changing the template default. Keep SQLite
deployments single-instance; SQLite is not a
horizontally scalable backend. Private ACR image pulls require an `AcrPull`
role assignment and managed-identity registry configuration. See the
[deployment profile](../deployment-profiles.md) for setup and health checks.

The [GitHub deployment workflow](../../.github/workflows/deploy-azure.yml)
builds and deploys the exact successful main-push CI commit after approval in
the `azure-demo` GitHub environment. It uses environment-bound Entra OIDC
federation rather than Azure passwords, pins the image digest, and checks health
and anonymous-read rejection. Configure environment reviewers, main-only branch
rules, and Azure variables using the
[GitHub Actions setup guide](../deployment-profiles.md#github-actions-deployment).
Use the repository's configured immutable OIDC subject prefix when creating
Azure federation; a name-only subject causes `AADSTS700213`. The setup guide
documents exact subject discovery and retry without relaxing approvals.
The workflow becomes active only after it is merged to the default branch.

Intended scope:

- REST and MCP endpoints;
- managed identity;
- private networking;
- health and readiness endpoints;
- deployment slots;
- autoscale;
- application configuration;
- secretless patterns.

## AKS profile — roadmap/current priority

Intended scope:

- horizontally scalable runtime;
- event workers/projectors;
- source-system adapters;
- Entra Workload Identity;
- private networking;
- Key Vault integration;
- probes;
- autoscaling;
- workload isolation;
- controlled rollout.

## NVIDIA profile

GPU acceleration is optional and must not become a baseline dependency.

The architectural rule is:

> CPU/reference semantics remain authoritative; GPU acceleration is an execution optimization.

## Observability — next priority

OpenTelemetry coverage should include:

- query execution;
- repository access;
- function calls;
- policy decisions;
- MCP tool calls;
- actions;
- adapters;
- projectors.

Desired telemetry:

- latency;
- success/failure;
- trace correlation;
- retry/reconciliation signals.

Industrial data must not be leaked into telemetry by default.

## SRE direction for later releases

Production platformization will require:

- SLOs/SLIs;
- HA architecture;
- backup/restore;
- disaster recovery;
- capacity planning;
- multi-tenancy isolation;
- secrets lifecycle;
- vulnerability management;
- upgrade/rollback automation;
- performance benchmarking.
