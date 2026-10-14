# CEPIO migration manifests

Breaking ontology contract changes are not silently permitted.

When `scripts/check_ontology_compat.py` detects a breaking change, copy the exact
change key printed by the gate into a YAML manifest in this directory. A manifest
must explain why the break is intentional and how downstream data/applications
will migrate.

Example:

```yaml
schema_version: '1'
id: rename-industrial-old-equipment
from_ref: f29c5b43dcb94a997c7ab201dd64e4849ce721d2
description: Replace the legacy equipment type with the canonical asset type.
issue: '#123'
changes:
  - change: class_removed:industrial:https://cepio.org/ontology/industrial#OldEquipment
    rationale: The old type duplicated the canonical Equipment contract.
    strategy: deprecate-then-remove
    replacement: https://cepio.org/ontology/industrial#Equipment
    notes: Consumers must migrate stored type IRIs before removal.
```

Allowed strategies are:

- `alias`
- `rewrite`
- `dual-read`
- `manual`
- `deprecate-then-remove`
- `no-data-impact`

A migration declaration never waives CEPIO semantic-version requirements.
For pre-1.0 modules, a breaking change requires at least a minor version bump.
For modules at 1.0 or later, a breaking change requires a major version bump.

The accepted baseline is pinned in `compatibility/baseline.yaml`. Advance that
baseline only as an explicit release/contract acceptance change.
