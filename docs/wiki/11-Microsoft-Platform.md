# Microsoft Platform Extension

## Principle

CEPIO is Microsoft-native in implementation direction while remaining portable in canonical semantics.

```text
                    MICROSOFT DATA + AI
                            |
            +---------------+---------------+
            |               |               |
          DATA           AI / AGENTS     IDENTITY
            |               |               |
     Fabric / OneLake    Foundry           Entra
     Warehouse           Agents
     Lakehouse           MCP
     Eventhouse
            |               |
            +-------+-------+
                    |
                    v
                   CEPIO
      +-----------------------------+
      | Objects                     |
      | Relationships               |
      | State + Time                |
      | Provenance                  |
      | Functions                   |
      | Decisions                   |
      | Governed Actions            |
      | Policy                      |
      +--------------+--------------+
                     |
             Application runtime
```

## Platform responsibilities

| Microsoft capability | CEPIO role |
|---|---|
| Fabric / OneLake / RTI | enterprise data foundation and source bindings |
| Fabric IQ / Ontology / Graph | Microsoft-native materialization of CEPIO semantic objects/relationships |
| Microsoft Foundry | model and agent execution grounded through CEPIO tools |
| Entra | authenticated human, app and agent identity |
| Azure App Service | planned managed REST/MCP hosting profile |
| AKS | planned scale-out runtime/adapters/projectors profile |
| Purview | future/deferred catalogue, governance and lineage bridge |

## Fabric IQ binding

CEPIO can generate a Microsoft-native semantic deployment bundle:

```text
CEPIO canonical modules
          |
          v
FabricIQBindingGenerator
          |
     +----+----+
     v         v
ontology.ttl   binding-manifest.json
     |         |
     +----+----+
          v
      Fabric IQ
```

The binding preserves:

- canonical IRIs;
- module ownership/version;
- source mappings;
- entity keys;
- contract hashes;
- graph eligibility metadata.

Supported reference source types include:

- Lakehouse;
- Warehouse;
- Eventhouse/KQL;
- SQL Database;
- Mirrored Database;
- Semantic Model.

## Foundry + MCP

Foundry agents interact through the governed CEPIO MCP gateway rather than directly with raw enterprise data sources.

Identity originates from Entra/hosting context and is mapped to CEPIO actor context.

## Entra

Entra should establish authenticated actor identity for:

- humans;
- service principals;
- applications;
- AI/agent workloads.

The model must not be allowed to claim arbitrary roles through tool parameters.

## App Service

Current roadmap target for lightweight managed hosting:

- REST + MCP APIs;
- managed identity boundary;
- VNet/private connectivity;
- health/readiness endpoints;
- deployment slots;
- autoscale;
- secretless configuration patterns.

## AKS

Current roadmap target for scale-out deployment:

- runtime services;
- adapters;
- projectors;
- event workers;
- workload identity;
- private networking;
- Key Vault integration;
- probes/autoscaling;
- workload isolation;
- auditable rollout patterns.

## Purview

Purview is useful but intentionally non-blocking for v0.4.

Potential later integration:

- Purview asset to CEPIO `SourceReference` mapping;
- governance/classification context;
- lineage publication;
- domain/catalog links.

CEPIO remains authoritative for runtime operational provenance.
