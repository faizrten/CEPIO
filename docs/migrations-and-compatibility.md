# Ontology migrations and compatibility gates

CEPIO ontology definitions are production contracts. A change to a class,
relationship, datatype property, hierarchy edge, domain/range constraint,
namespace, or property contract can affect stored data, applications, agents,
Fabric bindings, and customer profiles.

## Compatibility model

CEPIO compares the current ontology contract with an immutable accepted Git
commit pinned in `compatibility/baseline.yaml`.

The gate classifies changes as:

- **additive** — a new module, class, relationship, or datatype property;
- **breaking** — removal of a module/class/relationship/property, namespace
  change, removal/change of hierarchy or domain/range/datatype constraints,
  or a new constraint on an already-existing semantic subject;
- **declared breaking** — a breaking change whose exact change key is covered
  by a migration manifest;
- **invalid** — semantic changes without the required module version bump,
  duplicate declarations, or stale migration declarations.

A declared breaking change is reviewable and may pass CI. It is not treated as
backward compatible.

## Semantic-version policy

Any semantic change requires the owning module version to increase.

- additive changes: patch or higher;
- breaking changes while the module major version is `0`: minor or major;
- breaking changes for `1.x` and later: major.

Migration manifests cannot override this rule.

## Intentional breaking change workflow

1. Change the ontology contract.
2. Bump the affected module version in `ontology-modules.yaml`.
3. Run:

   ```bash
   PYTHONPATH=src python scripts/check_ontology_compat.py
   ```

4. For each intentional break, copy the exact `BREAKING:` change key into a
   YAML file under `compatibility/migrations/`.
5. Record the rationale, migration strategy, replacement (when applicable),
   and tracking issue.
6. Rerun the compatibility gate. Intentional breaks become
   `DECLARED BREAKING`; undeclared breaks still fail.
7. Review migration impact in the PR before merge.

## Why the baseline is a Git commit

The baseline pins the complete CEPIO contract—module catalogue, ontology files,
and canonical property contract—without duplicating a large generated snapshot.
CI checks out full Git history and reconstructs the baseline snapshot offline
with `git archive`. No cloud service or network call is required.

The initial v0.4 baseline is the P0-complete main commit
`f29c5b43dcb94a997c7ab201dd64e4849ce721d2`.

## Advancing the baseline

Do not automatically move the baseline on every merge. Advance it deliberately
at a release/contract acceptance point so migrations remain auditable relative
to a known contract. A baseline-advance PR should identify the release, confirm
all declared migrations have been applied or accepted, and update
`compatibility/baseline.yaml`.

## CI

CEPIO CI performs the compatibility gate after unit tests:

```bash
PYTHONPATH=src python scripts/check_ontology_compat.py \
  --json-report compatibility-report.json
```

A non-zero exit blocks the PR when there is an undeclared breaking change,
semantic-version violation, duplicate declaration, or stale declaration.
