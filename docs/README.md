# CEPIO Documentation

This directory contains CEPIO's technical documentation and the curated CEPIO Wiki.

## Start here

- **[CEPIO v0.4 Developer Preview](developer-preview.md)** — clean-environment install, startup, qualification and release boundary.
- **[CEPIO Wiki](wiki/Home.md)** — narrative, navigable documentation for product, architecture, ontology, runtime, APIs, integrations, operations, roadmap and glossary.
- **[Architecture](architecture.md)** — authoritative runtime architecture notes.
- **[Execution Roadmap](roadmap.md)** — detailed implementation and release roadmap.

## v0.4 public API and operations

- [API v1 client guide](api-client-guide.md)
- [API reliability semantics](api-reliability.md)
- [Representative API examples](api-examples.md)
- [REST security / Microsoft Entra](rest-security.md)
- [Typed query contract](query-contract.md)
- [Query load baseline](query-load-baseline.md)
- [API versioning](api-versioning.md)
- [Reference deployment profiles](deployment-profiles.md)
- [Observability / OpenTelemetry](observability.md)

## Key technical contracts

- [Temporal state projection](temporal-state-projection.md)
- [Microsoft platform extension](microsoft-platform-extension.md)
- [Foundry + MCP](foundry-mcp.md)
- [Migrations and compatibility](migrations-and-compatibility.md)
- [Type identity and versioning](type-identity-and-versioning.md)
- [Property normalization](property-normalization.md)
- [Domain module normalization](domain-module-normalization.md)

## Integrations

- [Microsoft Fabric / Fabric IQ](integrations/microsoft-fabric-iq.md)
- [NVIDIA cuGraph](integrations/nvidia-cugraph.md)

## Documentation model

The documentation is intentionally split into two layers:

1. **`docs/wiki/`** — the explanatory and navigational layer for readers.
2. **Technical documents in `docs/`, ontologies, mappings, shapes and code** — the authoritative executable/design contracts.

When the two differ, the implementation contracts and accepted architecture decisions in the repository are authoritative. The wiki should be updated as part of material CEPIO capability and release changes.
