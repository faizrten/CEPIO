# Deployment and Operations

## Current state

CEPIO can run locally and has an Azure-hosted reference composition. Deployment is no longer only a future architecture topic; current mainline includes authenticated hosted REST, read-only Management and Streamable HTTP MCP surfaces, secretless GitHub/Azure OIDC deployment foundations, optional Azure AI Search runtime support and reference App Service/AKS profiles.

This does **not** mean CEPIO has completed the v0.8 OPERATE enterprise-runtime gate. Production distributed persistence, HA, queues/workers, SLO/DR and penetration/security qualification remain open.

## Local/reference deployment

Requires Python 3.11+.

```bash
git clone https://github.com/faizrten/CEPIO.git
cd CEPIO
python -m pip install -e '.[dev]'
pytest -q
make validate
```

For the public API in development/test mode:

```bash
CEPIO_ENVIRONMENT=test \
CEPIO_DB_URL=memory:// \
CEPIO_AUTH_MODE=dev \
uvicorn cepio.public_api:app --reload
```

For the hosted composition, use the documented `cepio.host_api:app` deployment path rather than assuming the development command above exposes Management or MCP.

## Hosted surface composition

Current hosted target:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

Security boundaries remain distinct:

- `/api/v1/*` uses normal CEPIO application identity/policy;
- `/management/v1/*` requires an authorized management reader/admin and remains GET/read-only;
- `/mcp` binds verified hosting identity into CEPIO actor context and does not let callers self-assert roles.

Anonymous access to protected Management/MCP surfaces is a deployment failure.

## Persistence

SQLite remains a durable **reference** implementation, not the target horizontally scalable production data plane.

Keep SQLite deployments single-instance unless the persistence topology is intentionally replaced.

Enterprise-grade distributed persistence is part of the v0.8 OPERATE qualification program.

## App Service profile

The reference App Service path now supports the hosted CEPIO composition and approved Azure demo workflow patterns.

Current deployment characteristics include:

- containerized CEPIO host;
- Entra/OIDC-based identity boundaries;
- GitHub Actions -> Azure federated OIDC deployment without stored Azure passwords;
- immutable-image/digest-oriented deployment checks;
- health and anonymous-auth-boundary validation;
- optional Azure AI Search runtime extra;
- hosted MCP runtime dependency/profile;
- managed-identity patterns for Azure resource access.

The Azure demo/deployment workflow remains a reference qualification environment, not a production SLO/HA guarantee.

## GitHub OIDC deployment

The deployment workflow uses environment-bound Entra federation rather than long-lived Azure secrets.

This repository uses an immutable GitHub OIDC subject configuration. Azure federated credentials must match the repository's actual immutable subject prefix exactly; a legacy name-only subject can produce `AADSTS700213`.

See the focused deployment/OIDC documentation for current setup and recovery instructions.

## Azure AI Search

Azure AI Search is an optional runtime adapter for CEPIO Retrieval & Indexing.

Deployment principles:

- use managed identity / `DefaultAzureCredential`, not Search API keys committed into CEPIO;
- the Search index is a rebuildable projection of bounded CEPIO memory metadata/evidence references;
- tenant/expiry boundaries are pushed into filters and revalidated by CEPIO after retrieval;
- Search does not become semantic authority or raw industrial source storage by default.

Live scale qualification remains separate from existence of the adapter implementation.

## Management projection

The remote Management surface is intentionally authenticated and read-only.

It supports Studio/control-plane observation without exposing:

- mutation commands;
- credentials;
- raw environment variables/secrets;
- source payloads;
- policy/authority mutation;
- package installation authority.

Browser experiences should generally consume the surface through an appropriate server-side/BFF boundary rather than holding CEPIO bearer tokens directly.

## Hosted MCP gateway

The hosted `/mcp` endpoint uses the official MCP Streamable HTTP server path and shares CEPIO authentication/actor mapping with the hosted runtime.

Key invariants:

- missing/invalid authentication fails closed;
- actors without mapped CEPIO authority fail closed;
- tool schemas do not accept caller-selected CEPIO roles;
- DNS-rebinding host/origin protections apply;
- normal CEPIO policy still governs Functions, Skills, recommendations and Actions.

A hosted MCP endpoint is protocol productization; it is not proof that every Foundry/Copilot scenario has been live-qualified.

## Foundry live qualification

A Reliability G1 qualification path is implemented for Microsoft Foundry Agent Service.

The initial G1 profile is deliberately least-privilege and Decision-focused. It can expose governed reads/Functions/Skill evaluation while excluding Action execution at the host tool-profile level.

A repository merge makes the qualification path available. It does not claim a live G1 PASS without actual Foundry environment evidence.

## AKS profile

AKS remains the reference direction for later scale-out qualification:

- horizontally scalable services;
- event workers/projectors;
- source-system adapters;
- workload identity;
- private networking;
- Key Vault integration;
- probes/autoscaling;
- workload isolation;
- controlled rollout and recovery.

The product still needs real distributed queue/lease/recovery and HA persistence qualification before v0.8 OPERATE can close.

## Observability

Observability is no longer merely a future priority. CEPIO already has backend-neutral telemetry/OpenTelemetry hooks for important runtime paths.

Production operations still require expanded end-to-end qualification for:

- hosted REST / Management / MCP;
- workflow steps;
- Skill invocation;
- retrieval/index adapters;
- source bindings;
- Action verification/reconciliation;
- queue/worker health;
- dependency degradation/backpressure.

Industrial/customer data must not leak into telemetry by default.

## SRE / OPERATE gate

v0.8 OPERATE still requires:

- production persistence topology;
- horizontal scale / HA;
- distributed queue/event processing;
- leases/recovery semantics;
- retries/DLQ/backpressure and circuit breakers;
- backup/restore;
- disaster recovery exercises;
- security/penetration qualification;
- capacity planning;
- measured SLOs / error budgets;
- operational dashboards/runbooks;
- upgrade/rollback qualification.

## Current claim boundary

- **Hosted reference deployment:** available.
- **v0.4 FOUNDATION release:** qualified.
- **v0.5 CONNECT:** current, not yet qualified.
- **v0.8 OPERATE:** not qualified.

See [Current State](../current-state.md), [Deployment Profiles](../deployment-profiles.md), [Remote Management](../remote-management-read-projection.md), [Foundry + MCP](../foundry-mcp.md) and [Roadmap](17-Roadmap.md).
