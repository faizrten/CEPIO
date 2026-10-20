# CEPIO Engineering Brief — Current Mainline

## Mission

Build CEPIO as the **portable Industrial Operating Intelligence layer for Energy & Process Industries**.

> **Thin infrastructure. Thick Industry IQ.**

CEPIO should own reusable industrial operating competence while binding — not recreating — authoritative enterprise systems, data platforms, generic agent runtimes and frontier-model infrastructure.

Palantir Ontology remains a useful capability benchmark, not CEPIO's product identity.

For the Microsoft reference ecosystem:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

Microsoft Foundry, Copilot, Fabric, Entra and Azure supply generic platform/runtime capabilities. CEPIO supplies industrial semantics, evidence, competence, Decisions, authority, governed Actions and Outcomes.

## Current product posture

- **Published release:** CEPIO v0.4 FOUNDATION — Developer Preview.
- **Current release gate:** CEPIO v0.5 CONNECT — Live Industrial Integration, open / partial.
- **Canonical v1 maturity score:** 69/100 at the governed scorecard snapshot; do not infer a new score from later merges.
- **Repository mainline:** intentionally contains foundations pulled forward from later releases. Component completion is not release qualification.

Before changing release status, consult:

- `docs/current-state.md`;
- `docs/roadmap.md`;
- `config/v1-scorecard.yaml`;
- `docs/governance/v1-scorecard-governance.md`;
- `RELEASE.md`.

## Architecture invariant

```text
Authoritative enterprise context
        |
        v
Replaceable bindings
        |
        v
Thin CEPIO operating core
        |
        v
Thick Industry IQ
        |
        v
Governed capability / memory / retrieval / execution runtime
        |
        v
REST · Management · MCP
        |
        v
Apps · Studio · copilots · agents
```

Use the rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

### CEPIO Core should remain thin

Core-level abstractions include only broadly reusable operating contracts such as:

- canonical identity, objects and relationships;
- events and operational state;
- valid time and transaction time;
- evidence and provenance;
- uncertainty/confidence;
- Functions and Decisions;
- governed Actions;
- policy, authority and audit;
- compatibility/migration contracts.

Do not add a canonical Core concept merely because a source system, customer schema, standard or one scenario contains that field/term.

### Industry IQ is where differentiated product value should accumulate

Prefer reusable capability packages containing:

- domain semantic compositions;
- personas and competency questions;
- evidence requirements;
- Skills/procedures;
- failure/degradation/risk patterns;
- decision/intervention patterns;
- constraints;
- KPI/performance/economic logic;
- governed workflows;
- evaluation and assurance contracts.

The success signal is **rising industrial competency with decreasing Core churn**.

## Current mainline foundations — do not regress

### Semantic, temporal and evidence contracts

- canonical modular CEPIO ontology architecture;
- IRI-first identity and fail-closed ambiguity handling;
- canonical datatype/property registry and authority metadata;
- property-level provenance and source references;
- valid-time and transaction-time history;
- deterministic event ordering/projection;
- governed uncertainty, confidence and information-gain semantics.

### Kinetic / governance contracts

- typed Functions;
- first-class Decision records;
- governed Actions;
- preconditions and approval metadata;
- actor/action/target-scoped idempotency;
- policy evaluation before external side effects and replay;
- durable workflow definitions/instances;
- human approval, retries/timeouts/cancellation and supported compensation;
- external Action verification/reconciliation;
- immutable `WorkflowOutcome`;
- exact policy-version pinning and trusted policy-evaluation lineage.

### Skills and application contracts

- Skill Registry and dependency contracts;
- runtime binding and READY preflight;
- READY-only host dispatch;
- executable Skill boundary through restricted governed host capabilities;
- application-contract/protocol convergence across REST, SDK and MCP;
- recommendation remains separate from execution authority.

### Platform and binding contracts

- provider-neutral Binding Contract;
- Fabric/Fabric IQ semantic binding and live-proof transport path;
- OSDU-first subsurface boundary;
- external identity/write/verify/reconcile foundation;
- Azure AI Search as optional rebuildable retrieval projection, never semantic authority.

### Industry IQ control plane

- Industry IQ Pack Registry;
- Capability Registry;
- governed Domain Onboarding and Compounding Industrial Intelligence;
- trusted catalogue/provenance;
- supply-chain attestation/SBOM/security policy;
- explicit global/domain/profile knowledge boundaries.

### Memory / retrieval / acceleration

- durable Semantic / Procedural / Episodic / Profile memory contracts;
- tenant-safe MemoryStore boundary;
- bounded ContextAssembler;
- capability-routed Retrieval & Indexing;
- deterministic rank fusion and required-evidence checks;
- Compiled Industry IQ deterministic bundles and bounded cache;
- PROFILE/customer context prohibited from shared compiled cache.

### Performance intelligence

- Performance Contract and runtime;
- industry -> organization -> role/persona -> individual specialization;
- explicit patches/suppressions with fail-closed dependency validation;
- objectives, KRs, KPIs, guardrails, accountability and contribution relationships;
- recommendation-only workflow response bridge;
- organization-neutral Refinery and Drilling Contractor Industry Performance Reference Packs.

### Hosted surfaces

The production-host composition is intentionally separated:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

Do not merge Management mutation or credential/configuration surfaces into the public application contract without an explicit architecture/governance decision.

## Microsoft-native industrial agency boundary

Do not build a second generic agent framework inside CEPIO.

Foundry/Copilot or other host runtimes may own:

- generic model invocation;
- agent lifecycle/session execution;
- generic orchestration infrastructure;
- generic tool transport.

CEPIO owns:

- industrial capability identity;
- evidence requirements;
- Skills;
- Decisions;
- industrial policy/authority;
- governed Actions;
- Outcomes and industrial assurance.

Agent/tool callers must never receive raw repositories, source-system clients or customer credentials merely for convenience.

## Current critical path — v0.5 CONNECT

The release gate requires real industrial proof, not more semantic breadth.

Critical sequence:

```text
live PI / historian evidence
    -> CEPIO asset/state/provenance
    -> Reliability Industry IQ / Skill
    -> consequence + uncertainty
    -> Decision
    -> policy / approval
    -> governed workflow
    -> SAP Action
    -> source read-back
    -> verification / reconciliation
    -> Outcome
```

Priority open proof areas:

- live SAP S/4HANA/EAM qualification;
- live PI/historian qualification;
- third authoritative source domain;
- K-201 three-source end-to-end proof;
- authorized/idempotent writeback;
- read-back, verification and reconciliation.

Do not declare v0.5 complete because workflow, Binding Contract, Fabric, Reliability semantics or external-action foundations exist independently.

## Product roadmap taxonomy

Use these capability labels consistently for **product releases**:

- **v0.4 FOUNDATION** — coherent developer/runtime foundation;
- **v0.5 CONNECT** — authoritative live industrial context and governed writeback;
- **v0.6 EXECUTE** — governed verified industrial outcomes/reference applications;
- **v0.7 EXTEND** — independent teams can safely add Industry IQ;
- **v0.8 OPERATE** — enterprise runtime dependability;
- **v0.9 GENERALIZE** — real cross-enterprise/platform portability;
- **v1.0 GUARANTEE** — stable production guarantees.

Component, Skill, Lab, ontology-module, pack and API versions remain independent. Never rename historical versioned artifacts merely to match product-release labels.

## Scorecard boundary

`config/v1-scorecard.yaml` is authoritative for the numeric v1 completion percentage.

Rules:

- never derive a new percentage from intuition;
- open PRs do not earn score;
- merged implementation does not automatically earn score;
- qualified/merged/main evidence must satisfy the scorecard's governed evidence contract;
- score drift should be surfaced and corrected through a governed PR.

Roadmap release gates and the v1 maturity score are separate systems.

## Customer-data / learning boundary

Customer operational data and profile knowledge must not silently train or mutate global CEPIO Industry IQ.

- tenant/profile memory remains scoped;
- customer-specific mappings, thresholds, formulas, procedures and policies remain customer-owned unless intentionally generalized through governed evidence;
- PROFILE capabilities cannot justify global CORE/COMMON promotion by themselves;
- protected Industry IQ/evaluation assets remain outside the public repository where publication would expose differentiated IP.

## Security invariants

1. Policy evaluation precedes external side effects and authorized replay.
2. Agents receive only authorized objects, properties, capabilities and tools.
3. Human approval cannot be represented by an AI role asserting a flag.
4. Audit, source evidence and historical records remain append-only through ordinary APIs.
5. Provenance cannot be fabricated by normal domain Action handlers.
6. Adapter failures reconcile explicitly; local success never implies external success.
7. Temporal/history access enforces the same actor/property authorization as current-state reads.
8. Observability, retrieval, compiled cache and management surfaces must not bypass tenant/actor authorization.
9. Derived/rebuildable projections must never become semantic or source-of-truth authority.
10. Breaking ontology/application/API contracts require explicit migration/versioning evidence.

## Documentation policy

Documentation is part of the product contract.

A PR that materially changes user/developer-visible capability, architecture, semantics, protocols, platform integration, security/governance, deployment, product positioning, release status or roadmap state must update documentation in the same PR.

At minimum consider:

- `docs/current-state.md` — when the mainline capability narrative changes materially;
- `README.md` — when product positioning, primary interfaces or major capability families change;
- `docs/README.md` — when a new focused document or Wiki page is added;
- `docs/wiki/Home.md` — when navigation or product-level narrative changes;
- `docs/architecture.md` / `docs/wiki/03-Architecture.md` — when architecture boundaries change;
- `docs/roadmap.md` / `docs/wiki/17-Roadmap.md` — when release-gate state changes;
- `docs/version-naming.md` — when version taxonomy changes;
- `RELEASE.md` — only when the published release boundary itself changes; do not rewrite historical release guarantees simply because `main` moved ahead.

Focused technical docs and ADRs remain authoritative for their bounded contracts.

Historical benchmark files should remain historical evidence. If their framing is superseded, add context or links rather than falsifying the historical result.

## Definition of done for engineering changes

A change is not complete until:

- relevant automated tests/qualification pass;
- source-neutral and customer/IP boundaries remain intact;
- security/policy/authority invariants remain intact;
- compatibility/migration obligations are satisfied;
- documentation is updated or an explicit no-documentation-impact rationale is recorded;
- product-release or scorecard claims are changed only through their own governed evidence gates.
