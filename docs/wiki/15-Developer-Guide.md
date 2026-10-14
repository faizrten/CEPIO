# Developer Guide

## Repository orientation

Major repository areas include:

```text
ontologies/             Canonical RDF/OWL modules
ontology-modules.yaml   Module catalogue and dependencies
mappings/               Source mappings + property contract
shapes/                 SHACL validation
src/cepio/              Runtime implementation
examples/               Executable examples/reference scenarios
actions/                Action definitions/contracts
integrations/           Integration implementation assets
deploy/                  Deployment assets
 deployments/            Platform deployment contracts
docs/                    Architecture/technical documentation
compatibility/           Semantic compatibility baselines/contracts
policies/                Policy-related assets
```

## Development workflow

```bash
python -m pip install -e '.[dev]'
pytest -q
make validate
```

The validation path should be treated as part of the semantic product, not only code quality.

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
