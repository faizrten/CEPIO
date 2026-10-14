# CEPIO type identity and ontology module versioning

## Decision

CEPIO canonical type identity is the full RDF IRI. Local names such as `WorkOrder` are convenience aliases only and are accepted by the runtime when they resolve unambiguously.

This is required to safely load canonical CEPIO modules alongside customer profiles and external vocabularies, where identical local names are expected.

```text
https://cepio.org/ontology/industrial#WorkOrder   canonical CEPIO type
https://example.org/seo#WorkOrder                SEO profile/source type
https://example.org/ad#WorkOrder                 AD profile/source type
```

`WorkOrder` alone resolves only when exactly one registered type has that alias. When more than one type shares the alias, CEPIO fails closed and requires the caller to supply a qualified IRI.

## Module contract

`ontology-modules.yaml` is the machine-readable module catalogue. Each module declares an immutable module id, namespace IRI, semantic version, ontology file, architectural tier, stability level and dependencies/version constraints.

The module loader validates namespace uniqueness, semantic versions, dependency existence, version constraints and dependency cycles.

## Compatibility

CEPIO can snapshot the public semantic contract of each module: classes, relationships, inheritance, domains and ranges. Snapshot comparison labels additions separately from potentially breaking removals. A later release will add explicit migration manifests for intentional breaking changes.

## Backwards compatibility

The v0.2 object model still carries `type: str`. CEPIO does not force existing payloads to emit IRIs immediately. The registry resolves those strings to canonical IRIs at validation and reasoning boundaries. New customer/profile types that collide by local name must use qualified IRIs.
