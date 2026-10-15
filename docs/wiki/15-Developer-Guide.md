# Developer Guide

## Repository orientation

Major repository areas include:

```text
ontologies/             Canonical RDF/OWL modules
ontology-modules.yaml   Module catalogue and dependencies
mappings/               Source mappings + property contract
shapes/                 SHACL validation
src/cepio/              Runtime implementation
generalization/         Archetypes, personas, competency packs and standards benchmarks
examples/               Executable examples/reference scenarios
actions/                Action definitions/contracts
integrations/           Integration implementation assets
deploy/                  Deployment assets
deployments/             Platform deployment contracts
docs/                    Architecture/technical documentation
docs/wiki/               Reader-oriented explanatory wiki
compatibility/           Semantic compatibility baselines/contracts
policies/                Policy-related assets
```

## Development workflow

```bash
python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python scripts/run_generalization_harness.py
```

The validation path should be treated as part of the semantic product, not only code quality.

## Generalization and competency testing

The Generalization Lab tests whether CEPIO's canonical/domain semantics can support materially different Energy & Process Industry operating questions without silently relying on LLM world knowledge or customer-specific concepts.

Harness v0.1 provides a frozen drilling-contractor competency pack and deterministic semantic-readiness evaluator. A result is tied to both a frozen-batch hash and the ontology-module hash. `PASS` means the required ontology terms and edge contracts exist; it does not yet prove runtime data or answer correctness.

When a valid competency exposes a gap, do not immediately add vocabulary. Classify the gap first as:

```text
CORE | DOMAIN | PROFILE | MAPPING | REJECT
```

Future live challenger/operator/judge agents remain evidence-constrained: model output alone is not enterprise truth and no harness agent may autonomously promote a gap into canonical CEPIO Core.

See [Generalization & Competency Harness](../generalization-harness.md).

## Documentation is part of the definition of done

A material CEPIO capability change is incomplete until the corresponding documentation is updated in the **same pull request**.

Changes that normally require documentation updates include:

- ontology modules, classes, properties, relationships and profiles;
- REST API, Python SDK, CLI, MCP tools and query behavior;
- runtime, persistence, temporal/provenance, graph and policy behavior;
- functions, decisions, actions and authorization semantics;
- Microsoft/NVIDIA integrations and industrial source adapters;
- deployment, security, observability and governance;
- migration/versioning/compatibility contracts;
- standards federation and supported mappings;
- examples, reference scenarios and applications;
- release status and roadmap milestones.

CEPIO documentation has two complementary layers:

1. **Authoritative technical contracts** — ontology files, code, mappings, SHACL shapes and focused technical docs.
2. **`docs/wiki/`** — the navigable explanatory layer for developers, architects and users.

Both must remain consistent.

When no documentation update is necessary, the pull request must explicitly select **No documentation impact** and explain why. The repository pull-request template requires this declaration.

### PR definition-of-done checklist

```text
[ ] implementation is tested
[ ] semantic validation passes where applicable
[ ] compatibility is preserved or migration is declared
[ ] authorization boundaries remain intact
[ ] examples/reference scenarios are updated where needed
[ ] relevant focused technical docs are updated
[ ] relevant docs/wiki page(s) are updated
[ ] README/docs navigation is updated when discoverability changes
[ ] roadmap/release status reflects reality when implementation status changes
```

## Adding a canonical ontology concept

Before adding a new class or property, ask:

1. Is the concept already represented in CEPIO?
2. Does an external standard provide authoritative semantics?
3. Is it generic enough for canonical CEPIO or should it be a profile extension?
4. Which module owns it?
5. What relationships connect it to existing CEPIO primitives?
6. Does it require a migration/version change?

## Adding a property

A property should define:

- canonical IRI;
- datatype/range;
- owning module;
- semantic meaning;
- authority expectations;
- mapping behavior;
- provenance requirements.

## Adding a relationship

Define:

- canonical IRI;
- domain;
- range;
- cardinality where meaningful;
- inverse relationship if appropriate;
- temporal behavior;
- intended traversal semantics.

## Adding a function

Define:

- stable function identity;
- typed inputs;
- typed output;
- applicable target type(s);
- authorization requirements;
- deterministic behavior expectations;
- test cases.

## Adding an action

In addition to function metadata, define:

- side effects;
- preconditions;
- policy requirements;
- idempotency behavior;
- expected object version behavior;
- audit fields;
- external adapter binding;
- acknowledgement/reconciliation semantics.

## Adding a source-system adapter

Keep the adapter below the canonical contract.

Do not expose source-specific fields directly to applications unless they are explicitly represented as profile/source extensions.

## Compatibility discipline

Ontology evolution requires semantic version discipline and, when breaking, migration manifests.

Typical policy:

```text
Additive semantic change
 -> patch or higher

Breaking pre-1.0 module change
 -> minor/major + migration manifest

Breaking 1.x+ module change
 -> major + migration manifest
```

## API discipline

New public interfaces should converge on the stable CEPIO resource model rather than proliferating one-off endpoints.

Prefer:

```text
objects
relationships
query
state
provenance
functions
actions
schema
```

over domain-specific endpoint duplication.
