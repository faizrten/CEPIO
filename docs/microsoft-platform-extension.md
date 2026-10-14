# CEPIO as a Microsoft Data + AI Platform Extension

## Architectural intent

CEPIO is not a standalone ontology product that happens to integrate with Microsoft services, and it is not a Fabric-only ontology package.

CEPIO is intended to be the **industrial semantic and operational extension layer for the Microsoft data, AI, governance and application platform**.

The canonical CEPIO contract remains portable and source-system-neutral. Microsoft services provide first-class deployment, storage, graph, governance, agent, application and infrastructure bindings.

```text
                         CUSTOMER / INDUSTRIAL REALITY
                                   │
                                   ▼
                         CEPIO CANONICAL CONTRACT
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
         Semantics             Operations            Governance
  Type · Property · Graph   Event · State · Action  Provenance · Policy
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                      MICROSOFT PLATFORM BINDINGS
                                   │
       ┌──────────────┬────────────┼─────────────┬─────────────┐
       │              │            │             │             │
    Fabric         Fabric IQ    Foundry       Purview      App Runtime
   OneLake       Ontology/Graph Agents/IQ   Governance     AppSvc / AKS
       │              │            │             │             │
       └──────────────┴────────────┼─────────────┴─────────────┘
                                   │
                                ENTRA
                        identity / authorization
```

## Non-negotiable design rule

Microsoft-specific bindings must not contaminate CEPIO-Core or the canonical industry modules.

A deployment can use Fabric IQ, Foundry, Purview, App Service and AKS without those services becoming prerequisites for CEPIO semantic correctness or for the CEPIO test suite.

Target relationship:

```text
CEPIO canonical contract
        │
        ├── Fabric binding
        ├── Fabric IQ binding
        ├── Foundry binding
        ├── Purview binding
        ├── App Service hosting profile
        └── AKS hosting profile
```

not:

```text
CEPIO Core
   └── hard-coded Fabric / Foundry / AKS semantics
```

---

# Platform responsibility model

## 1. Microsoft Fabric / OneLake — data foundation

### Microsoft responsibility

Fabric and OneLake provide analytical, operational and real-time data services that can hold or expose enterprise data bound into CEPIO.

Expected CEPIO bindings include:

- Lakehouse;
- Warehouse;
- SQL database;
- Power BI semantic models;
- Real-Time Intelligence / Eventstreams;
- Fabric APIs;
- OneLake shortcuts and governed enterprise data products.

### CEPIO responsibility

CEPIO defines:

- which industrial concept a source dataset represents;
- source-to-canonical mapping;
- identity resolution;
- canonical relationships;
- datatype/property semantics;
- event semantics;
- provenance;
- valid/transaction time semantics;
- operational actions.

### Boundary

Fabric stores/exposes enterprise data.
CEPIO supplies industrial meaning and operational contracts over that data.

---

# 2. Fabric IQ / Ontology / Graph — Microsoft-native semantic materialization

Fabric IQ should be treated as CEPIO's primary Microsoft-native **semantic realization layer**.

### Microsoft responsibility

Fabric IQ can materialize:

- business entity types;
- properties;
- relationships;
- rules / metrics;
- graph traversal;
- ontology-bound business data;
- agent grounding over enterprise business context.

### CEPIO responsibility

CEPIO remains the upstream canonical industrial definition for:

- namespace and type identity;
- reusable industry modules;
- semantic versions;
- compatibility rules;
- SEO / AD / future customer-profile mappings;
- industrial action and state contracts;
- cross-platform semantics.

### Binding principle

```text
CEPIO Asset
     │
     └── materialize / bind
               │
         Fabric IQ Entity
```

The Fabric IQ entity is a deployment representation of the CEPIO contract, not a replacement for CEPIO source-of-truth governance.

### Why this separation matters

Fabric IQ is an evolving platform capability. CEPIO must be able to adopt richer Fabric IQ features without breaking the canonical industrial contract or making the ontology unusable outside Fabric.

---

# 3. Microsoft Foundry — agent and AI execution plane

Foundry should be CEPIO's primary Microsoft-native **agent execution and AI application plane**.

### Microsoft responsibility

Foundry provides:

- model access;
- prompt and hosted agent runtimes;
- agent lifecycle;
- toolboxes;
- managed MCP/tool access;
- evaluation and observability;
- agent identity and enterprise security integration.

### CEPIO responsibility

CEPIO supplies the tools agents are allowed to reason and act through:

```text
get_object
get_object_at
get_object_valid_at
query
traverse
explain_property
explain_state
calculate_function
recommend_action
execute_action
rebuild_projection
```

All CEPIO tools remain authorization-aware.

### Target pattern

```text
Foundry Agent
     │
     ▼
Foundry Toolbox / MCP
     │
     ▼
CEPIO MCP Gateway
     │
     ├── Semantic Query
     ├── Temporal Query
     ├── Lineage
     ├── Functions
     └── Governed Actions
             │
             ▼
       Enterprise systems
```

Foundry decides how an agent runs.
CEPIO decides what industrial concepts/actions mean and whether an action is authorized.

---

# 4. Microsoft Purview — governance and enterprise lineage plane

Purview should complement, not replace, CEPIO provenance.

### Microsoft responsibility

Purview provides enterprise governance capabilities such as:

- Data Map metadata;
- catalog/discovery;
- data classification;
- governance domains;
- broader enterprise data lineage;
- stewardship and governance workflows.

### CEPIO responsibility

CEPIO maintains operationally precise provenance such as:

```text
Object
Property IRI
Source system
Source record
Source field
Mapping version
Transformation run
Observed time
Ingested time
Source value hash
Projector / Event provenance
```

### Integration direction

```text
Purview Data Asset
       │
       ├── source identity / governance metadata
       ▼
CEPIO SourceReference
       │
       ▼
PropertyProvenance / Object Provenance
```

and where appropriate:

```text
CEPIO transformation / materialization
       │
       └── publish lineage metadata → Purview
```

Purview gives enterprise-wide data governance.
CEPIO gives ontology-aware operational provenance and reasoning lineage.

---

# 5. Azure App Service — managed CEPIO application/API hosting

App Service is the default low-operations deployment option for CEPIO application services that do not require Kubernetes-level orchestration.

Suitable CEPIO workloads:

- REST API;
- MCP gateway;
- ontology administration application;
- lightweight domain applications;
- reference dashboards;
- customer-facing semantic APIs;
- web applications using CEPIO SDKs;
- domain-specific agent applications.

Target deployment features:

- Entra / managed identity;
- VNet integration;
- private endpoints where applicable;
- deployment slots;
- autoscale;
- Application Insights / OpenTelemetry;
- managed PaaS lifecycle.

App Service must remain a hosting profile rather than a semantic dependency.

---

# 6. Azure Kubernetes Service — scale and specialized runtime plane

AKS should be the CEPIO deployment option for high-throughput, containerized or specialized workloads.

Suitable workloads:

- CEPIO core runtime at high scale;
- high-throughput MCP/API services;
- event ingest processors;
- state projectors;
- customer-specific adapters;
- long-running optimization workloads;
- distributed workers;
- graph/materialization workers;
- isolation-heavy enterprise deployments;
- specialized industrial AI services.

Required design patterns:

- Entra Workload Identity;
- secretless service authentication where possible;
- Key Vault integration;
- private networking;
- policy/RBAC boundaries;
- health/readiness probes;
- autoscaling;
- structured observability;
- immutable deployment/version metadata.

AKS is infrastructure for CEPIO services, not ontology semantics.

---

# 7. Microsoft Entra — identity plane

Entra should provide the identity context used by every CEPIO deployment binding.

CEPIO policy evaluation should consume normalized identity attributes such as:

```text
Actor
  principal_id
  tenant_id
  workload_id
  roles
  groups
  application_id
  agent_id
  authentication_context
```

The same CEPIO action policy must apply whether the caller originates from:

- a Fabric workload;
- a Foundry agent;
- an App Service API;
- an AKS workload;
- a human application;
- an enterprise automation process.

---

# CEPIO Microsoft extension contracts

CEPIO should expose eight durable platform contracts.

## A. Semantic Contract

- module;
- namespace;
- class;
- relationship;
- property;
- datatype;
- inheritance/interface;
- version.

Bindings: **Fabric IQ, Fabric Graph, Fabric data models**.

## B. Data Binding Contract

- external source;
- identity mapping;
- source field;
- canonical type/property;
- relationship mapping;
- transformation.

Bindings: **Fabric / OneLake / external enterprise systems**.

## C. Query Contract

- type filter;
- property predicate;
- relationship traversal;
- transaction time;
- valid time;
- pagination / ordering;
- authorization context.

Bindings: **Fabric IQ/Graph, REST, MCP, SDK**.

## D. Event / State Contract

- source event;
- event time;
- subject;
- deterministic projector;
- derived state;
- checkpoint;
- replay.

Bindings: **Fabric RTI/Eventstreams, PI/AVEVA, AKS workers**.

## E. Provenance / Governance Contract

- source reference;
- mapping version;
- transformation;
- lineage;
- governance identity;
- classification reference.

Bindings: **Purview + CEPIO runtime provenance**.

## F. Agent / Tool Contract

- read tool;
- query tool;
- lineage explanation;
- temporal explanation;
- function invocation;
- action recommendation;
- governed action execution.

Bindings: **Foundry MCP / toolboxes, Copilot Studio**.

## G. Policy / Identity Contract

- actor identity;
- workload/agent identity;
- roles / claims;
- object/property/action permissions;
- approval requirements.

Bindings: **Entra + CEPIO policy engine**.

## H. Deployment / Observability Contract

- service identity;
- deployment version;
- module version;
- health;
- traces;
- metrics;
- audit correlation IDs.

Bindings: **App Service, AKS, Application Insights / OpenTelemetry**.

---

# Reference deployment patterns

## Pattern 1 — Fabric-native enterprise semantic deployment

```text
Enterprise Data
     │
Fabric / OneLake
     │
Fabric IQ Ontology + Graph
     │
CEPIO bindings
     │
Foundry Agent
```

Use where most data and analytics already live in Fabric.

## Pattern 2 — CEPIO managed application platform

```text
Fabric / SAP / OSDU / PI
          │
          ▼
     CEPIO Runtime
          │
    Azure App Service
      REST + MCP
          │
          ▼
     Apps / Foundry
```

Use for lower-operational-overhead enterprise deployments.

## Pattern 3 — Industrial-scale CEPIO runtime

```text
PI / DCS / Eventstreams / SAP / OSDU
                 │
                 ▼
        AKS CEPIO Services
    ┌────────────┼────────────┐
 Ingestors    Projectors    Adapters
    │            │             │
    └────────────┼─────────────┘
                 │
        CEPIO Runtime / MCP
                 │
         Fabric IQ / Foundry
```

Use for high-throughput/event-driven industrial workloads.

## Pattern 4 — Unified governance

```text
Purview Data Map / Governance
          │             ▲
          ▼             │
 CEPIO SourceRef     lineage publication
          │             │
          └── CEPIO Provenance
```

---

# Strategic positioning

The intended Microsoft architecture is therefore:

```text
MICROSOFT DATA + AI PLATFORM

Fabric / OneLake       = enterprise data foundation
Fabric IQ              = enterprise semantic intelligence materialization
Purview                = enterprise governance / catalog / broader lineage
Foundry                = models + agents + AI execution
App Service            = managed CEPIO application/API hosting
AKS                    = scaled/specialized CEPIO runtime hosting
Entra                  = identity and workload trust

                         │
                         ▼
                    CEPIO EXTENSION

Industrial concepts
Industrial relationships
Lifecycle semantics
Asset/process/EPCIC/drilling semantics
Industrial provenance
Bitemporal state
Industrial events
Functions
Decisions
Actions
Agent tools
Policy boundaries
```

CEPIO should make Microsoft services understand and operate **energy and asset-heavy industrial enterprises in a common language**.

That is the architectural objective for all future CEPIO releases.
