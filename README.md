# CEPIO

**Common Energy & Process Industry Ontology**

> **An industry operating ontology for Energy & Process Industries — connecting enterprise data, operational state, industrial semantics, AI reasoning and governed action.**

## North Star

> **Aim for CEPIO to provide the same class of enterprise operating abstraction that Palantir Ontology provides — specialized for Energy & Process Industries and natively realized across the Microsoft ecosystem.**

CEPIO provides a canonical model of industrial **objects, relationships, state, time, provenance, functions, decisions and governed actions**.

The intended operating loop is:

```text
Observe -> Understand -> Reason -> Decide -> Recommend -> Authorize -> Act -> Observe outcome
```

Applications and AI agents should be able to operate on the enterprise without embedding business logic directly into SAP, AVEVA PI, OSDU, Primavera P6, Fabric tables, SQL schemas or another source-system representation.

---

## Current release

Current Python package version: **`0.4.0`**.

Release designation: **CEPIO v0.4 — Developer Preview**.

v0.4 qualifies CEPIO as a coherent Microsoft-native developer/runtime contract rather than only a repository-level ontology reference. The supported public HTTP surface is `/api/v1`.

Start with:

- [Developer Preview guide](docs/developer-preview.md)
- [Release manifest and support boundary](RELEASE.md)
- [Execution roadmap](docs/roadmap.md)
- [CEPIO Wiki](docs/wiki/Home.md)

The Developer Preview is intentionally narrower than a production enterprise platform. SQLite remains a single-writer reference backend, live industrial-system writeback is v0.5 work, and production HA/SLO/DR qualification is later roadmap work.

---

## What CEPIO is

CEPIO is an **industrial operating abstraction** between enterprise systems and the applications, agents and workflows that consume them.

```text
Enterprise reality
        |
        v
Source systems
SAP · PI · OSDU · P6 · MES · Fabric · SQL
        |
        v
      CEPIO
+--------------------------------+
| Objects                        |
| Relationships                  |
| Properties                     |
| Events + State                 |
| Valid time + Transaction time  |
| Provenance                     |
| Functions                      |
| Decisions                      |
| Actions                        |
| Policies                       |
| Migration contracts            |
+---------------+----------------+
                |
       +--------+--------+
       v                 v
     Apps              Agents
       |                 |
       +--------+--------+
                v
       Governed operations
```

CEPIO is **not** another data lake, graph database product, generic RDF/OWL standards project, agent framework or plant-control system. CEPIO defines industrial meaning and the governed operating contract; platform services implement and materialize that contract.

---

## Architecture principle

CEPIO separates three concerns:

```text
1. CEPIO Canonical Model
   What an industrial enterprise means
            |
            v
2. Platform Bindings
   How CEPIO is realized on technology platforms
            |
            v
3. Customer Profiles
   How a particular enterprise operates
```

> **Microsoft services may implement CEPIO capabilities, but they do not define CEPIO's industrial semantics.**

SAP schemas, PI tags, Fabric tables, OSDU objects and customer-specific models may map into CEPIO without becoming canonical CEPIO semantics by default.

---

## CEPIO operating model

CEPIO combines semantics, operational state and kinetics:

```text
                           CEPIO
                             |
          +------------------+------------------+
          |                  |                  |
      SEMANTICS            STATE             KINETICS
          |                  |                  |
      Objects              Events             Functions
      Relationships        Time               Decisions
      Properties           History            Actions
      Interfaces           Provenance         Workflows*
      Capabilities         Projection         Constraints
          |                  |                  |
          +------------------+------------------+
                             |
                      Policy + Audit
                             |
                       Apps + Agents
```

`*` Individual functions, decisions and actions are executable today. Durable first-class workflow orchestration is roadmap issue #67 rather than a v0.4 guarantee.

---

## What v0.4 includes

### Semantic + state foundation

- modular CEPIO Core / Industrial / Energy / Lifecycle / Enterprise / Kinetic ontology;
- canonical Asset, Work Management, Reliability, HSE, Supply, Performance, Workforce, Commercial and Agentic Operations modules;
- Process Industry, Manufacturing, EPCIC and Drilling domain modules;
- IRI-first type/property identity and fail-closed alias ambiguity;
- canonical property contract;
- property-level provenance;
- bitemporal object and relationship history;
- deterministic event -> state projection.

### Kinetic runtime

- typed functions;
- first-class Decision records;
- governed Actions;
- preconditions and approval metadata;
- compensation-handler support;
- action audit;
- actor/action/target-scoped idempotency.

### Public API v1

- versioned `/api/v1` namespace;
- committed OpenAPI route baseline;
- 18 route/method/operation-ID contracts enforced in CI;
- structured error envelopes and request correlation;
- ETag / If-Match optimistic concurrency;
- Idempotency-Key action semantics;
- typed object queries, deterministic cursors and query budgets;
- graph analytics, events, functions, decisions and audit endpoints.

The v0.4 OpenAPI guarantee is intentionally **route-contract based plus selected product-critical semantics**. It is not yet a claim of complete generated-schema compatibility for every request/response field.

### Security

- Microsoft Entra token validation for production mode;
- actor identity and roles derived from validated claims rather than request authority;
- explicit development-auth mode that fails closed in production;
- object-type, sharing-scope, property, function and action controls;
- query authorization before exposed totals, cursor positions and pages.

### Microsoft platform extension

- Fabric / Fabric IQ semantic binding;
- Microsoft Foundry + governed CEPIO MCP integration;
- App Service reference deployment profile;
- AKS reference deployment profile;
- managed/workload identity boundaries documented separately from CEPIO actor identity.

### Observability

- backend-neutral telemetry event/sink contract;
- repository, policy, function and action latency/success/failure telemetry;
- sanitized rejected-action telemetry;
- optional OpenTelemetry adapter.

### Graph intelligence

- NetworkX CPU/reference graph analytics;
- PageRank, degree, betweenness and eigenvector centrality;
- Louvain communities;
- dependency traversal and blast radius;
- optional NVIDIA `nx-cugraph` acceleration path.

---

## Time, provenance and state

CEPIO distinguishes:

- **valid time** — when a fact is true in the industrial domain;
- **transaction time** — when CEPIO recorded or learned that fact.

This lets CEPIO distinguish:

```text
What was actually true at time T?
vs.
What did CEPIO believe at time T?
```

Property provenance can retain source system, source entity/field/record, source-value hash, mapping version, transformation run, observed time and ingestion time.

Operational state is rebuildable from immutable events with deterministic `(occurred_at, event_id)` ordering.

---

## Microsoft-native architecture

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
      | Objects + Relationships     |
      | State + Time + Provenance   |
      | Functions + Decisions       |
      | Governed Actions + Policy   |
      +--------------+--------------+
                     |
             App Service / AKS
```

| Platform | CEPIO role |
|---|---|
| **Fabric / OneLake / RTI** | enterprise data foundation and operational/analytical source bindings |
| **Fabric IQ / Ontology / Graph** | Microsoft-native materialization of CEPIO semantic objects and relationships |
| **Microsoft Foundry** | model/agent execution grounded through governed CEPIO tools |
| **Microsoft Entra** | authenticated human, application and agent identity |
| **Azure App Service** | managed CEPIO REST/MCP reference hosting profile |
| **AKS** | containerized CEPIO reference hosting profile |
| **Purview** | deferred governance/catalog/lineage bridge |

---

## Foundry + governed MCP

CEPIO exposes governed MCP tools for Microsoft Foundry agents, including object/query access, temporal state, provenance explanation, function calls, recommendations and authorized action execution.

Identity is injected from the authenticated hosting context; actor ID and roles are not model-callable authority.

```text
Microsoft Foundry Agent
          |
          | authenticated identity
          v
     CEPIO MCP Gateway
          |
          +-- read policy
          +-- property filtering
          +-- function authorization
          +-- action policy
          +-- preconditions
          +-- audit
          |
          v
      CEPIO Runtime
```

Recommendation is intentionally separate from execution. An AI agent can be permitted to inspect evidence and recommend an action while remaining unable to execute it.

---

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/faizrten/CEPIO.git
cd CEPIO
python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python examples/demo.py
```

Start the supported public API locally:

```bash
CEPIO_ENVIRONMENT=test \
CEPIO_DB_URL=memory:// \
CEPIO_AUTH_MODE=dev \
uvicorn cepio.public_api:app --reload
```

Open `http://localhost:8000/docs` and use `/api/v1/...` routes.

For a clean wheel/container install, follow [docs/developer-preview.md](docs/developer-preview.md).

### Python client

```python
from cepio.sdk import CEPIOClient

client = CEPIOClient(
    "http://127.0.0.1:8000",
    dev_actor="developer",
    dev_roles={"cepio_admin"},
)
print(client.health())
client.close()
```

### TypeScript client

Reference source is under `clients/typescript/cepio.ts`. Both Python and TypeScript operation maps are checked against the same OpenAPI v1 route baseline in CI.

### Container

```bash
docker build -t cepio:v0.4 .
docker run --rm -p 8000:8000 \
  -e CEPIO_ENVIRONMENT=test \
  -e CEPIO_DB_URL=memory:// \
  -e CEPIO_AUTH_MODE=dev \
  cepio:v0.4
```

The final image is built from the CEPIO wheel and does not rely on an editable source checkout.

---

## Developer Preview qualification

The release CI validates:

```text
pytest
query pushdown/load regression
App Service + AKS deployment invariants
public API v1 route contract
Python + TypeScript client route contract
ontology compatibility
SHACL validation
reference refinery demo
clean wheel build/install outside checkout
wheel-only container build/start/API health
```

Read [RELEASE.md](RELEASE.md) for supported vs experimental/deferred functionality.

---

## Standards federation

CEPIO federates strong external industry semantics rather than recreating them. Current or targeted references include:

`OSDU`, `ISA-95 / IEC 62264`, `ISO 15926`, `CFIHOS`, `DEXPI`, `BIM / IFC`, and selective `FIBO` concepts where appropriate.

The Digital Twin Consortium Manufacturing Ontologies corpus is federated as an external ISA-95 / IEC 62264 semantic source. See `docs/standards/dtc-isa95-manufacturing.md` and `THIRD_PARTY_NOTICES.md`.

> **Reuse reference semantics where they are strong; retain CEPIO as the operating abstraction that connects those semantics across the enterprise.**

---

## Repository structure

```text
ontologies/                     canonical CEPIO RDF/OWL modules
ontology-modules.yaml           module catalogue, versions and dependencies
mappings/                       source mappings + canonical property contract
shapes/                         SHACL validation contracts
src/cepio/                      runtime, query, temporal, provenance, policy, SDK
src/cepio/integrations/microsoft/
                                Fabric IQ + Foundry/MCP bindings
openapi/                        accepted public API v1 route baseline
clients/typescript/             TypeScript reference client
compatibility/                  accepted ontology baseline + migration manifests
actions/                        declarative actions
policies/                       authorization examples
deploy/                         App Service, AKS and optional runtime profiles
deployments/                    platform deployment artifacts
examples/                       refinery reference data and demos
tests/                          semantic/runtime/platform/API/compatibility tests
docs/                           Developer Preview, architecture, standards, roadmap, wiki
```

---

## Roadmap

### Completed foundations

- **v0.1 Semantic Scaffold** — modular ontology architecture.
- **v0.2 Operational Kernel** — persistence, policy, decisions, actions, audit and SDK foundations.
- **v0.3 Temporal + Provenance Kernel** — provenance, bitemporal history and deterministic event-state reconstruction.
- **v0.4 Microsoft Platform Extension / Developer Preview** — stable public API route contract, Entra boundary, query scale/cursors, Microsoft hosting profiles, observability and release qualification.

### v0.5 — Live Industrial Integration

Focus: source-neutral onboarding/extractor runtime, adapter contract, SAP/PI and additional industrial integrations, identity reconciliation, governed writeback and a live compressor reference scenario.

### v0.6 — Kinetic Runtime + Reference Industrial Applications

Focus: first-class workflow orchestration (#67) followed by Asset Reliability / Maintenance Command Center (#59), then additional industrial operating applications.

### Later platformization

- v0.7 developer platform / CLI / scaffolding;
- v0.8 enterprise runtime, HA, queues, SLOs and DR;
- v0.9 second-enterprise portability proof;
- v1.0 explicit production guarantees.

See [docs/roadmap.md](docs/roadmap.md) for the authoritative execution plan.

---

## Documentation

- [Developer Preview](docs/developer-preview.md)
- [API clients](docs/api-client-guide.md)
- [API reliability semantics](docs/api-reliability.md)
- [API examples](docs/api-examples.md)
- [REST security](docs/rest-security.md)
- [Query contract](docs/query-contract.md)
- [Query load baseline](docs/query-load-baseline.md)
- [Deployment profiles](docs/deployment-profiles.md)
- [Observability](docs/observability.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Wiki](docs/wiki/Home.md)

---

## Design philosophy

CEPIO is not intended to become a large collection of disconnected ontology classes.

Its purpose is to create an **operational model of the enterprise**:

```text
enterprise evidence
       |
       v
industrial meaning
       |
       v
operational state
       |
       v
reasoning
       |
       v
decision
       |
       v
authorized action
```

Industrial enterprises already have enormous amounts of data. The harder problem is connecting that data to **meaning, context, state, decisions and action**.

```text
DATA
  +
SEMANTICS
  +
TIME
  +
PROVENANCE
  +
REASONING
  +
GOVERNED ACTION
  =
INDUSTRIAL OPERATING ABSTRACTION
```

That is the direction of CEPIO.
## Code quality and governance

See [CEPIO Code Quality & Governance v2](docs/governance/code-quality-governance-v2.md)
for automated quality evidence, release qualification, and exact ruleset setup.
