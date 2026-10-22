# ADR-0039 — Retire Azure AI Search; Prefer PostgreSQL for CEPIO Memory and Retrieval

- **Status:** Accepted
- **Date:** 2026-10-22
- **Supersedes:** ADR-0032 Azure AI Search Adapter; ADR-0038 Azure Search Throttling
- **Scope:** CEPIO public runtime, deployment, retrieval configuration and roadmap

## Context

The Azure AI Search adapter was an optional, rebuildable physical projection
behind source-neutral RetrievalBackend and MemoryStore contracts. Live-scale
qualification reached index creation after RBAC repair but later encountered
request throttling during ingestion; a 50K pass was not established. CEPIO Labs
has separately validated PostgreSQL-backed inference cost-ledger storage, but
the public CEPIO reference application still supports in-memory/SQLite
repositories and does **not** yet support PostgreSQL as its primary datastore.

The decision is to prioritize industry knowledge, decision intelligence and
governance over maintaining a separate managed Search service.

## Decision

1. **Retire Azure AI Search from active CEPIO.** Remove the adapter, optional
   Search SDK dependency, Search-specific CI and scale workflows, synthetic
   index harness, tests, active guide and runtime/deployment settings.
2. Preserve the governed MemoryStore, RetrievalBackend, ContextAssembler,
   source authority, tenant and expiry boundaries, provenance, bounded
   retrieval and all industrial policy/approval contracts.
3. **Prefer PostgreSQL** for a qualified CEPIO durable memory/retrieval
   implementation: relational metadata and structured/full-text retrieval
   first; pgvector only when a frozen eval justifies it.
4. Keep the qualified SQLite CEPIO runtime in service until a separate
   PostgreSQL Repository/MemoryStore adapter, migration/rollback, Entra
   identity, private connectivity, tenant isolation and performance
   qualification pass. An existing Labs cost ledger is not proof of an
   application datastore cutover.
5. Decommission the development Search **cloud resource** as a separate
   managed Azure lifecycle action only after verifying its resource group
   and that no other tenant or project depends on it. Remove obsolete Search
   role assignments and delete only the confirmed
   `cepio-search-dev-31d48` Search service. Do not remove PostgreSQL,
   Foundry, Fabric, or other unrelated Azure resources.
6. Preserve superseded Search ADRs as explicit historical context. No
   retroactive claim of successful 50K qualification or production SLO.

## Operational consequences

- The hosted CEPIO deployment installs only its active MCP runtime extra
  and clears legacy `CEPIO_AZURE_SEARCH_ENDPOINT` and
  `CEPIO_AZURE_SEARCH_INDEX` App Service settings without changing the
  configured SQLite repository.
- The Bicep reference App Service no longer declares Search parameters.
- Active navigation, guides and architecture documents reflect the
  PostgreSQL-first direction without claiming PostgreSQL mainline readiness.
- Cancel outstanding historical scale runs: a previously authorized
  waiting job could otherwise reset a shared development index.
- **Repository removal alone does not stop Azure Search billing.** Confirm
  actual Search-resource deletion via the Azure portal or scoped Azure CLI.

## Assurance and validation

Require the usual CEPIO governance, static/type, architectural,
compatibility, test, and deletion-aware coverage gates. Verify the
authenticated REST, Management and MCP deployment health boundaries remain
unchanged. No customer data is exported, migrated, copied to a search
service or used to train global knowledge in this retirement.
