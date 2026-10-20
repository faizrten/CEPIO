# Memory and Context

CEPIO separates **what Industry IQ remembers** from **what the model sees for one task**.

The architectural rule is:

> Industry IQ knowledge may compound continuously; runtime working memory remains bounded.

## Durable memory

CEPIO v0.1 recognizes four durable memory classes:

- **Semantic** — concepts and reusable industrial meaning.
- **Procedural** — skills, workflows, policies and reasoning procedures.
- **Episodic** — prior situations, decisions, incidents and outcomes.
- **Profile** — organization, site, asset, persona and customer-specific context.

Customer/profile memory stays tenant-scoped. A global memory record cannot contain tenant/customer-specific provenance.

## Working context

Working context is ephemeral. `ContextAssembler` receives candidate memories and admits only a bounded deterministic set based on priority, relevance and explicit budgets for tokens, capabilities, semantic nodes, evidence items and episodes.

Required context that cannot fit causes a fail-closed `BLOCKED` result. Optional context can be shed.

## Storage

CEPIO depends on a logical `MemoryStore` contract rather than a particular database. v0.1 provides an in-memory reference backend plus durable SQLite proof. PostgreSQL/Azure SQL, search indexes, caches, lake storage and federated stores can be introduced later behind the same contract.

Large industrial evidence should normally remain authoritative in source systems such as Fabric, SAP, PI, OSDU, ADX or Cognite. CEPIO stores compact memory, provenance and evidence references.

## Compounding

Operational memory does not automatically become global knowledge. Reusable knowledge must pass the existing Compounding Intelligence path: generalization, independent cross-domain evidence, regression qualification and human architecture approval before Capability Registry promotion.

See `docs/memory-context-architecture.md` and `docs/adr/ADR-0029-memory-context-architecture-v0.1.md` for the full design.
