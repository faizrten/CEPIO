# ADR-0014: Progressive Environment A on Azure App Service

Status: Proposed for PR #179

## Context

CEPIO needs a reproducible first cloud deployment that preserves the existing runtime contract while avoiding premature production complexity. The repository already contains a production Dockerfile, App Service deployment profile, CI, health checks, REST/MCP surfaces and governance gates. The next step is therefore not a new runtime architecture; it is a governed `LOCAL -> DEV` deployment path.

The current v0.4 reference persistence implementation supports `memory://` and `sqlite:///...` only. It intentionally rejects PostgreSQL URLs until a separate production repository adapter is implemented. Environment A must not claim or simulate PostgreSQL support by infrastructure configuration alone.

The deployment workflow itself is a protected governance path because it can create Azure resources and publish a runnable CEPIO image. It therefore requires explicit rationale, least-secret authentication and preservation of existing merge gates.

## Decision

Adopt the following reference pattern for Progressive Environment A:

```text
LOCAL
  -> existing CEPIO CI
  -> GitHub OIDC authentication to Azure
  -> Bicep provision/update
  -> Azure Container Registry Basic
  -> immutable CEPIO image tagged by Git SHA
  -> Azure App Service Linux B1
  -> `/api/v1/health` smoke test
```

Environment A is a synthetic/non-production environment. It uses the existing CEPIO container unchanged and stores the DEV reference SQLite database on persistent App Service `/home` storage.

The Azure web app receives a system-assigned managed identity. ACR admin credentials remain disabled. The web app receives `AcrPull` on the registry and is configured to use managed identity for image pulls.

GitHub Actions authenticates to Azure with OpenID Connect. No Azure client secret is stored in the repository or workflow. The federated identity is scoped to the GitHub `dev` environment, using the subject:

```text
repo:faizrten/CEPIO:environment:dev
```

The deployment workflow reuses the existing full CEPIO CI through `workflow_call`; Azure deployment is blocked if that qualification job fails. The deployed image is the immutable `GITHUB_SHA` image. The moving `:dev` tag is convenience-only and is not the deployment identity.

## Safety boundary

Environment A permits:

- synthetic datasets;
- ontology/runtime/API/MCP testing;
- read-only DEV integrations;
- agent experimentation;
- deployment and observability validation.

Environment A does not authorize:

- production customer data;
- production source-system credentials;
- production SAP/EAM writeback;
- OT/control-system commands;
- autonomous operational actions;
- production availability or durability claims.

No CEPIO Core semantic, policy, Action Runtime or source-system-neutrality invariant is changed by this decision.

## Persistence decision

Do not provision PostgreSQL as the active CEPIO DEV repository until the runtime contains and qualifies a PostgreSQL repository adapter behind the existing persistence abstraction.

Until then:

```text
CEPIO_DB_URL=sqlite:////home/data/cepio.db
```

is the Environment A persistence contract.

A future ADR or compatible implementation change may introduce PostgreSQL after repository-level tests prove parity for identity, state, temporal semantics, provenance, policy/action records and concurrency behavior.

## Validation

The change is acceptable only if:

1. existing CEPIO CI remains required and green;
2. governance and quality checks remain enforced;
3. the Bicep deployment creates the intended DEV resources without registry admin credentials;
4. the web app can pull the immutable image through managed identity;
5. `/api/v1/health` succeeds after deployment;
6. the deployed image can be traced to the exact Git commit;
7. no production data or external operational side effect is required to validate Environment A.

## Consequences

Positive:

- CEPIO obtains a real Azure deployment without introducing AKS, Service Bus, Redis or production database complexity prematurely;
- deployment provenance is commit-addressable;
- Azure credentials are not stored as long-lived workflow secrets;
- the cloud environment exercises the same packaged CEPIO artifact already qualified by CI;
- future TEST/PROD environments can extend the same pattern instead of inventing a second deployment model.

Trade-offs:

- App Service SQLite is a DEV reference persistence mechanism, not the final production state store;
- ACR public network access remains enabled in Environment A to keep the first deployment inexpensive and debuggable;
- private networking, APIM, multi-region resilience and production write paths are deliberately deferred.

## Follow-up

The next persistence milestone is a production repository adapter, expected to target PostgreSQL first. The next environment milestone after Environment A stabilizes is Progressive Environment B: `LOCAL -> DEV -> TEST` with stronger isolation, deployment approvals and production-like persistence/networking.
