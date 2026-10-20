# Microsoft Platform

## Principle

CEPIO is Microsoft-native in reference implementation while remaining portable in canonical industrial contracts.

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

Microsoft services may implement data, identity, hosting, retrieval and model/agent execution capabilities. They do not define CEPIO industrial semantics, evidence contracts, authority or Industry IQ.

```text
                    MICROSOFT DATA + AI
                            |
      +---------------------+----------------------+
      |                     |                      |
    DATA                AI / AGENTS             IDENTITY
      |                     |                      |
Fabric / OneLake         Foundry / Copilot       Entra
RTI / Warehouse          model + agent runtime
Azure AI Search          MCP client/host
      |                     |                      |
      +---------------------+----------------------+
                            |
                            v
                           CEPIO
         +----------------------------------------+
         | semantics · state · evidence · time    |
         | Industry IQ · Skills · Decisions       |
         | policy · authority · Actions · Outcomes|
         +--------------------+-------------------+
                              |
             REST · Management · hosted MCP
```

## Platform responsibilities

| Microsoft capability | CEPIO role |
|---|---|
| Fabric / OneLake / RTI | authoritative enterprise context and replaceable source binding |
| Fabric IQ / Ontology / Graph | Microsoft-native materialization of CEPIO semantic objects/relationships |
| Microsoft Foundry | generic model/agent execution consuming CEPIO contracts/tools |
| Copilot experiences | persona-adaptive experience/runtime above CEPIO contracts |
| Entra | authenticated human, application and agent identity |
| Azure App Service | current hosted reference composition for REST + Management + MCP |
| AKS | reference scale-out deployment direction/profile |
| Azure AI Search | optional rebuildable retrieval projection behind CEPIO retrieval contracts |
| Purview | future/deferred governance/catalog/lineage bridge |

## Fabric and Binding Contract

CEPIO separates semantic materialization from operational provider bindings.

Fabric/Fabric IQ can materialize canonical CEPIO objects/relationships while Binding Contract v0.1 provides a source-neutral operational evidence/action boundary.

```text
Fabric / OneLake / SQL endpoint
          |
          v
Microsoft-specific reader/transport
          |
          v
CEPIO Binding Contract
          |
          v
provider-neutral Industry IQ / Skill / Decision
```

The transport is Microsoft-specific; the industrial capability is not.

The current Fabric live-proof path uses a dedicated synthetic proof schema and compares semantic/behavioral results to a source-neutral provider baseline. A merged transport path is not automatically a live production qualification.

See [Microsoft Fabric Live Binding Proof](../integrations/microsoft-fabric-live-binding-proof.md).

## Foundry + CEPIO industrial agency

Foundry agents should interact through authenticated CEPIO Application/MCP contracts rather than direct access to raw enterprise sources, repositories or credentials.

```text
Foundry-hosted agent
        |
generic reasoning / agent lifecycle
        |
        v
CEPIO MCP / Application Contract
        |
        +--> governed evidence reads
        +--> authorized Functions
        +--> READY Skill evaluation
        +--> Decision/recommendation
        +--> separately authorized Action path
```

CEPIO retains authority over:

- capability identity;
- evidence requirements;
- Skill admission/readiness;
- Decision semantics;
- policy/authority;
- governed Actions;
- verified Outcomes.

The Reliability Agent Lighthouse formalizes this boundary. A G1 qualification path exists on main, with a least-privilege tool profile that excludes Action execution for the initial Decision-only proof. Repository implementation does not itself claim a successful live Foundry run.

See [Reliability Agent Lighthouse](../reliability-agent-lighthouse.md) and [Foundry Reliability G1](../foundry-reliability-g1.md).

## Entra

Entra establishes authenticated actor/workload identity for:

- humans;
- service principals;
- applications;
- AI/agent workloads.

Caller-visible CEPIO requests and MCP tools do not allow a model/client to self-assert CEPIO roles. Hosting middleware maps verified identity into CEPIO actor context.

## Hosted App Service composition

The hosted CEPIO target composition now includes three separated surfaces:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

The container host composes these surfaces while preserving their distinct authority contracts.

- Application REST remains the normal governed application boundary.
- Management is read-only observation/control-plane projection.
- MCP reuses CEPIO authentication/policy and host-injected identity.

See [Remote Management Read Projection](../remote-management-read-projection.md) and [Foundry + MCP](../foundry-mcp.md).

## Azure AI Search

Azure AI Search is an optional physical backend behind CEPIO Retrieval & Indexing.

It is explicitly a **rebuildable retrieval projection**:

- Capability Registry / MemoryStore remain authoritative;
- tenant and expiry constraints are pushed into Search and rechecked after retrieval;
- customer/source raw data is not automatically copied into the index;
- Search ranking never grants authority or bypasses ContextAssembler budgets.

See [Azure AI Search Adapter](../azure-ai-search-adapter.md).

## AKS

AKS remains the reference direction for scale-out/runtime qualification involving:

- services and distributed workers;
- adapters/projectors;
- event processing;
- workload identity;
- private networking;
- probes/autoscaling;
- workload isolation;
- controlled rollout/recovery.

Enterprise HA/SLO/DR and distributed persistence/queue qualification remain later OPERATE release-gate work.

## Purview

Purview remains useful but non-blocking.

Potential integration includes:

- Purview asset -> CEPIO `SourceReference` mapping;
- classification/governance context;
- lineage publication;
- catalog/domain links.

CEPIO remains authoritative for runtime industrial provenance/decision/action lineage even when Purview is used as an enterprise catalog/governance service.

## Portability test

Microsoft-native must not become Microsoft-dependent.

A strategic success criterion is that the same CEPIO competency/Skill/Decision contract can operate when enterprise context is supplied through different underlying providers such as Fabric, Cognite or OSDU-based environments.

The platform changes; the industrial operating contract should not.
