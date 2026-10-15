# CEPIO Customer Profiles

CEPIO separates the canonical Energy & Process Industry contract from customer-specific semantics.

```text
Canonical CEPIO
    |
    +-- Customer Profile: SATORP
    +-- Customer Profile: ARO
    +-- Customer Profile: ...
```

A customer profile may map source concepts, add customer-specific ontology classes, provide deployment bindings, define validation shapes and policies, and carry reference/sample data without making those concepts canonical by default.

## Directory contract

```text
profiles/
  <profile-id>/
    profile.yaml
    ontology.ttl
    mappings/
    bindings/
    shapes/          # optional
    actions/         # optional
    policies/        # optional
    sample-data/     # optional
```

`profile.yaml` is the profile contract. Example:

```yaml
schema_version: '1'
id: satorp
version: 0.1.0
namespace: https://cepio.org/profile/satorp#
depends_on:
  core: '>=0.2.0'
  industrial: '>=0.2.0'
  asset: '>=0.1.0'
  process_industry: '>=0.1.0'
files:
  ontology:
    - ontology.ttl
  mappings:
    - mappings/seo_customer_to_cepio.csv
  bindings:
    fabric_iq: bindings/fabric-iq.yaml
```

The loader validates that every declared file exists and that every canonical-module dependency satisfies the profile's version constraint. Unknown, incomplete or incompatible profiles fail closed.

## Runtime selection

Profiles are selected explicitly:

```text
CEPIO_PROFILES=satorp
```

or programmatically:

```python
runtime = build_runtime(profiles=["satorp"])
```

The runtime builds its type registry from canonical ontology plus selected profile ontology. Profile versions are exposed as runtime metadata and through `/health`.

An unselected profile must have no effect on canonical type identity or runtime behavior.

## Fabric IQ

`generate_profiled_fabric_bundle(...)` composes canonical CEPIO Fabric IQ output with selected profile ontology and declared Fabric IQ binding profiles.

The canonical modules remain the semantic authority. Profile concepts remain in profile namespaces and are layered into deployment artifacts rather than promoted into canonical module namespaces.

## Promotion discipline

Use this decision hierarchy when deciding where a concept belongs:

```text
Customer-only concept
        -> customer profile

Repeated across customers in one industry/domain
        -> domain module

Repeated across Energy & Process industries
        -> industrial-common module

Fundamental cross-enterprise concept
        -> foundation/core
```

Promotion requires evidence of reuse. A single customer's terminology or implementation requirement is not sufficient reason to alter the canonical CEPIO model.

## SATORP reference profile

The first reference profile is `profiles/satorp/`.

The existing SEO normalization contained one explicitly customer-specific concept, `AmiralAsset`. It has been removed from canonical `mappings/seo_to_cepio.csv` and moved to the SATORP profile mapping. The profile ontology declares:

```text
satorp:AmiralAsset
    rdfs:subClassOf
asset:InstalledAsset
```

This preserves SATORP/Amiral terminology while keeping `asset:InstalledAsset` as the reusable CEPIO semantic.

Canonical normalization remains 41 SEO common mappings plus one SATORP profile mapping, preserving the original 42-source-concept coverage without putting a customer profile concept in canonical mapping scope.

## Engineering rule

Customer onboarding should primarily add or modify files under `profiles/<customer>/`. A customer requirement that changes canonical ontology, canonical property contracts or shared runtime behavior requires explicit evidence that the concept belongs at a higher reuse tier and must follow CEPIO semantic compatibility/migration governance.
