# Developer Guide

## Engineering North Star

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

When deciding whether to build something inside CEPIO, ask:

1. Is this reusable industrial operating intelligence?
2. Is it a stable CEPIO contract or generic infrastructure another platform already provides?
3. Can CEPIO bind the capability rather than own/rebuild it?
4. Does the change belong in Core, DOMAIN, PROFILE, MAPPING or should it be REJECTED?
5. What evidence/competency proves the change is needed?

Use:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

For Microsoft-hosted agent workloads:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

Do not build a second generic agent/model/session framework inside CEPIO merely because an agent use case exists.

## Repository orientation

Major areas include:

```text
ontologies/             Canonical RDF/OWL modules
ontology-modules.yaml   Module catalogue and dependencies
mappings/               Source mappings + property contract
shapes/                 SHACL validation
src/cepio/              Runtime/application/control-plane implementation
generalization/         Archetypes, personas, competency/eval assets
actions/                Action definitions/contracts
policies/               Policy assets
integrations/           Integration implementation assets
deploy/                  Reference infrastructure/deployment assets
deployments/             Platform/tool deployment contracts
compatibility/           Semantic/interface compatibility baselines
docs/                    Focused technical/architecture documentation
docs/wiki/               Reader-oriented narrative Wiki
config/                  Governed product/configuration contracts incl. v1 scorecard
```

## Current product status

Do not infer product release state from the code tree.

- v0.4 FOUNDATION — qualified published Developer Preview;
- v0.5 CONNECT — current / partial product gate;
- later release foundations are intentionally pulled forward on main;
- v1 scorecard currently remains 69/100 at its governed snapshot.

Before making release/product claims, read:

- [Current State](../current-state.md)
- [Execution Roadmap](../roadmap.md)
- [Version Naming](../version-naming.md)
- [v1 Completion Scorecard](../v1-completion-scorecard.md)
- `RELEASE.md`

## Development workflow

Typical local validation:

```bash
python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python scripts/run_generalization_harness.py
```

Use focused qualification scripts/workflows for the capability being changed; the full repository CI/governance gates remain authoritative.

Validation is part of the product contract, not merely code quality.

## Architecture boundaries developers must preserve

### Thin Core

Core should contain only broad reusable operating abstractions such as:

- canonical identity;
- objects/relationships/state;
- time;
- evidence/provenance;
- uncertainty/confidence;
- Functions/Decisions/Actions;
- policy/authority/audit;
- compatibility/migration.

Do not promote source/customer vocabulary merely for convenience.

### Thick Industry IQ

Prefer reusable capabilities/packs containing:

- domain semantic compositions;
- personas/competency questions;
- evidence requirements;
- Skills/procedures;
- failure/risk/decision patterns;
- performance/KPI/economic logic;
- constraints/authority;
- workflows;
- evaluation/assurance contracts.

### Replaceable bindings

Source/provider integrations belong behind the Binding Contract. Provider-specific transport must not define domain semantics.

### Derived runtime projections

Memory indexes, Azure AI Search and compiled caches are projections/acceleration mechanisms.

```text
Index != Source of Truth
Cache != Authority
```

## Generalization and competency testing

Generalization tests whether CEPIO remains reusable across materially different industrial operating questions without relying on hidden model world knowledge or customer-specific concepts.

Competency/assurance asks whether CEPIO can support the industrial decision through explicit semantics, runtime evidence, Skills and governed execution.

When a valid competency exposes a gap, classify it before adding vocabulary:

```text
CORE | DOMAIN | PROFILE | MAPPING | REJECT
```

- `CORE` — broadly reusable industrial operating semantics;
- `DOMAIN` — source-neutral domain specialization;
- `PROFILE` — customer/site/deployment specialization;
- `MAPPING` — external taxonomy/source vocabulary to federate;
- `REJECT` — literal requested concept is the wrong abstraction.

Accepted triage should remain executable/regression-tested.

No agent/harness may autonomously promote a gap into canonical Core.

See [Generalization & Competency Harness](../generalization-harness.md) and [Competency & Assurance](20-Competency-Assurance.md).

## Capability Registry, packs and Skills

Keep three responsibilities distinct:

```text
Capability Registry
= what CEPIO can legitimately claim it knows how to do

Industry IQ Pack Registry
= reusable industrial intelligence deployed into a runtime

Skill Registry
= procedures admitted/bound/READY for execution
```

A capability claim requires evidence. A pack being available does not make every Skill READY. A READY Skill does not grant Action authority.

## Memory / retrieval development discipline

Durable Industry IQ may grow continuously, but per-task working context must remain bounded.

When adding memory/retrieval functionality:

- preserve tenant/profile ownership;
- reject cross-tenant leakage;
- ensure global memory excludes customer-specific content;
- keep indexes rebuildable;
- recheck tenant/expiry after backend retrieval;
- require actual evidence for required capabilities;
- keep ContextAssembler budgets fail-closed;
- prohibit PROFILE/customer context from shared compiled caches.

## Performance Contract discipline

Industry reference performance semantics should remain organization-neutral.

Customer-specific values such as:

- formulas;
- targets;
- thresholds;
- organizational scope;
- individual accountability;
- source bindings;

belong in explicit specialization rather than canonical reference packs.

Do not turn reference accountability into employee-scoring truth.

## Adding a canonical ontology concept

Before adding a class/property/relationship, ask:

1. Is the concept already represented?
2. Can a composition of existing concepts satisfy the capability?
3. Does an external standard already provide authoritative semantics?
4. Is the concept generic enough for Core/common semantics?
5. Should it be DOMAIN, PROFILE or MAPPING instead?
6. Which module owns it?
7. What competency/evidence demonstrates the need?
8. What compatibility/migration impact follows?

Ontology growth is not itself a success metric.

## Adding a property

Define:

- canonical IRI;
- datatype/range;
- owner module;
- semantic meaning;
- authority expectations;
- mapping behavior;
- provenance requirements;
- temporal behavior where relevant.

Avoid domain-only scalars when the concept is naturally a reusable value object with units, currency, validity or provenance.

## Adding a relationship

Define:

- canonical IRI;
- domain/range;
- cardinality where meaningful;
- inverse relationship if appropriate;
- temporal behavior;
- intended traversal semantics;
- evidence strength.

Do not strengthen weak evidence into stronger assertions without justification.

## Adding a Function

Define:

- stable identity;
- typed inputs/output;
- applicable target types;
- authorization requirements;
- deterministic expectations;
- provenance/evidence assumptions;
- tests.

## Adding a Skill

Define:

- stable Skill identity/version;
- required object/relationship/evidence capabilities;
- Functions/Decisions/Actions required;
- runtime bindings;
- authority assumptions;
- preflight behavior;
- allowed side-effect posture;
- competency/evaluation fixture;
- pack/version dependencies.

Skills execute through restricted governed hosts, not raw runtime/source clients.

## Adding an Action

Define:

- side effect;
- target identity;
- preconditions;
- policy/authority;
- idempotency;
- concurrency expectations;
- audit;
- source binding;
- acknowledgement/read-back;
- verification/reconciliation;
- compensation semantics if supported.

External local success must not be interpreted as source success until verified/reconciled.

## Adding a provider/source binding

Implement provider-specific transport below the CEPIO Binding Contract.

Preserve:

- canonical identity;
- evidence/provenance;
- event/observation time;
- error/failure semantics;
- authenticated Action boundary;
- source verification/reconciliation.

Do not expose provider-specific fields directly to applications unless they are explicit source/profile extensions.

## Adding an agent integration

Prefer host-platform execution and CEPIO industrial agency.

Agent integrations should:

- use authenticated host identity;
- expose least-privilege tool profiles;
- consume CEPIO Application/MCP contracts;
- avoid raw repositories/source clients/credentials;
- separate Decision/recommendation from Action execution;
- produce explicit live qualification evidence before claiming a real environment PASS.

## Compatibility discipline

Do not renumber artifacts merely to align them with product roadmap versions.

Product, runtime component, Lab benchmark, pack, Skill, ontology module and API versions are independent.

Breaking semantic/interface changes require the appropriate migration/version contract.

See [Version Naming](../version-naming.md).

## Documentation is part of definition of done

A material CEPIO capability change is incomplete until documentation is updated in the **same PR**.

Changes that normally require documentation updates include:

- product positioning / architecture boundaries;
- ontology/modules/profiles;
- Application Contract, REST, SDK, MCP or Management;
- runtime / workflow / policy / Skills;
- Industry IQ / Capability Registry / pack trust;
- Memory / Retrieval / Compiled IQ;
- Performance Contracts/packs;
- source/provider integrations;
- deployment/security/observability;
- compatibility/versioning;
- competency/generalization/evaluation;
- release/roadmap/scorecard status.

### Documentation surfaces to consider

```text
[ ] focused technical doc / ADR updated
[ ] tests/qualification describe actual claim boundary
[ ] docs/current-state.md updated if mainline story changed materially
[ ] root README updated if major product/interface capability changed
[ ] docs/README.md index updated if discoverability changed
[ ] Wiki Home/navigation updated if a page/capability was added
[ ] Wiki architecture/runtime/security/integration page updated where relevant
[ ] roadmap updated only if release-gate state/scope changed
[ ] version-naming updated only if taxonomy changed
[ ] RELEASE.md changed only if published release boundary changed
[ ] scorecard changed only through governed scorecard evidence
```

When no documentation update is needed, the PR should explicitly explain why.

## Product-claim discipline

Never turn one of these into another without evidence:

```text
merged code
    != product release qualification

synthetic/reference proof
    != live environment proof

semantic PASS
    != runtime/agent/operational PASS

open PR
    != canonical v1 score
```

This discipline is part of CEPIO's product quality, not administrative overhead.
