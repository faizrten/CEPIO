# Security and Governance

## Security objective

CEPIO can influence enterprise Decisions and invoke governed external Actions. Security, identity and authority therefore belong inside the operating contract, not only in UI or platform configuration.

Current security design must cover not only reads/actions, but also Skills, workflows, hosted MCP, Management, memory/retrieval, Industry IQ pack admission and customer/global knowledge boundaries.

## Actor context

An actor may represent:

- human user;
- application;
- service principal;
- integration workload;
- AI agent.

Actor identity must originate from authenticated hosting context and be mapped into CEPIO roles/authority.

Identity/roles are not caller- or model-selectable business parameters.

```text
BAD
cepio_execute_action(actor_role="admin", ...)

GOOD
Verified host identity -> CEPIO actor context -> policy / authority
```

## Core authority invariants

```text
Knowledge != Authority
Recommendation != Execution
Model Output != Evidence
Index != Source of Truth
Cache != Authority
```

A user/agent can be permitted to understand evidence or propose a Decision while remaining unable to execute the resulting Action.

## Read and evidence policy

Read authorization may apply to:

- object types;
- specific objects;
- properties;
- relationship classes;
- provenance/evidence detail;
- temporal history;
- tenant/profile memory;
- retrieval results;
- Management descriptors.

Authorization should occur before sensitive result counts, cursor positions, evidence bundles or model context are exposed.

## Function and Skill authorization

Functions and Skills are separate governed capability surfaces.

A Skill must pass runtime/actor-aware READY preflight before execution. Skill procedures receive restricted governed host capabilities rather than raw repository/source-system clients.

Function permission, Skill permission, Decision authority and Action authority remain separable.

## Action authorization

Actions require stronger controls:

- authenticated actor context;
- policy/role/authority checks;
- target constraints;
- state preconditions;
- approval requirements;
- optimistic concurrency where relevant;
- actor/action/target-scoped idempotency;
- immutable audit;
- external verification/reconciliation for source writes.

Policy is evaluated before replaying idempotent results so idempotency cannot become an authorization bypass.

## Workflow governance

Durable workflow instances pin trusted policy/version context and preserve approval/execution lineage.

Governance includes:

- exact policy version binding;
- trusted canonical context derivation;
- human pause/resume;
- deny-dominant composition where applicable;
- Action authorization at execution time;
- compensation only for supported governed Actions;
- external verification before final successful Outcome where required.

## Hosted MCP boundary

The hosted `/mcp` gateway is authenticated and binds verified request identity into CEPIO actor context.

Important rules:

- MCP tool schemas do not contain caller-selected roles;
- actors without mapped CEPIO authority fail closed;
- normal CEPIO policy remains authoritative for Functions, Skills, recommendations and Actions;
- host/origin protections apply to Streamable HTTP transport;
- a least-privilege host profile can remove Action tools entirely for qualification scenarios.

For Microsoft-hosted agents:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

## Management boundary

`/management/v1/*` is a separate authenticated **read-only** projection.

It must not expose:

- mutation commands;
- policy/authority modification;
- credentials/secrets;
- raw environment variables;
- customer/source payloads;
- package installation authority;
- runtime back doors around the Application Contract.

Least-privilege management-reader identity is preferred over broad admin where supported.

## Memory and tenant governance

Durable memory distinguishes global and customer/profile scopes.

Rules include:

- global memory must not contain tenant/customer-specific knowledge;
- tenant/profile memory has explicit ownership;
- cross-tenant access fails closed;
- customer operational memory does not silently become global Industry IQ;
- PROFILE/customer context is prohibited from shared Compiled Industry IQ cache.

## Retrieval and cache governance

Retrieval/index services are derived projections and must not become authority.

- tenant/expiry constraints are enforced during planning and rechecked after backend retrieval;
- required evidence must actually be present, not inferred from rank score;
- optional search/vector/graph backends cannot bypass final ContextAssembler budgets;
- cache/index loss must be recoverable from authoritative contracts/data;
- cache contents must not grant maturity, policy or execution authority.

Future PostgreSQL search projections must follow these same boundaries.

## Industry IQ pack trust

External/reusable Industry IQ pack admission is host-controlled.

The trusted-catalogue and supply-chain model can enforce:

- trusted source/publisher;
- artifact SHA-256 binding;
- host-verified publisher attestations;
- SBOM evidence;
- vulnerability scan evidence;
- atomic admission;
- deployment provenance.

A signature reference alone is not treated as cryptographic verification. Skills/agents do not gain discovery/install/upgrade/trust-policy authority.

## Customer-data / IP boundary

Customer-specific data, mappings, formulas, targets, thresholds, procedures, policies and learned operational behavior remain customer/profile-owned unless an explicit governed generalization process approves a safe reusable abstraction.

Protected CEPIO Industry IQ/evaluation assets may remain outside the public repository when publication would expose differentiated intelligence.

## Performance governance

Industry Performance Reference Packs are organization-neutral hypotheses, not universal company truth.

Customer organizations explicitly specialize:

- formulas;
- targets/thresholds;
- scopes;
- accountability;
- response bindings.

Reference persona accountability must not be interpreted as automatic employee scoring or individual ownership.

## Audit

High-value operations should retain immutable/auditable records for:

- policy outcomes;
- Skill readiness/execution;
- Decision creation;
- approvals;
- Action request/dispatch;
- external acknowledgement;
- verification/reconciliation;
- workflow Outcomes;
- actor identity;
- timestamps;
- relevant object/workflow versions;
- source/pack provenance where relevant.

## Ontology and compatibility governance

Semantic governance includes:

- module ownership/versioning;
- namespace stability;
- migration manifests;
- compatibility gates;
- SHACL validation;
- explicit acceptance of breaking changes.

No customer/source field should enter canonical Core solely because one system exposes it.

## Enterprise defense in depth

CEPIO policy complements rather than replaces source/platform security:

```text
Source-system controls
 -> platform/data controls
 -> CEPIO identity / evidence / policy
 -> application/agent permissions
 -> governed external execution
 -> source verification/reconciliation
```

## Product-governance boundaries

- `docs/roadmap.md` controls release-gate narrative.
- `config/v1-scorecard.yaml` controls numeric v1 maturity.
- `RELEASE.md` controls the published v0.4 guarantee.
- merged component capability does not automatically change any of those claims.

See [Current State](../current-state.md), [Code Quality & Governance v2](../governance/code-quality-governance-v2.md) and [IP Publication Policy](../governance/ip-publication-policy.md).
