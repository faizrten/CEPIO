# CEPIO Microsoft Fabric / Fabric IQ Binding

CEPIO v0.4 treats Microsoft Fabric and Fabric IQ as a **platform binding** of the canonical CEPIO industrial operating ontology.

> CEPIO defines the industrial semantics. Fabric materializes, binds, queries, governs and operationalizes those semantics.

The binding must not make CEPIO-Core dependent on a Fabric workspace, tenant, credential, preview API, storage engine, or item format.

## Current Fabric IQ target

As of October 2026, Fabric IQ Ontology is in preview. The public experience supports entity types, properties, inheritance, relationships, data bindings, metrics and an optional ontology-managed Graph. Fabric can import external TTL/RDF/RDFS/OWL ontology content and export ontology content for round-trip validation.

Current Microsoft documentation:

- Fabric IQ: https://learn.microsoft.com/fabric/iq/
- Ontology overview: https://learn.microsoft.com/fabric/iq/ontology/overview
- Import/export ontology: https://learn.microsoft.com/fabric/iq/ontology/how-to-import-export
- Bind data: https://learn.microsoft.com/fabric/iq/ontology/how-to-bind-data
- Ontology Graph: https://learn.microsoft.com/fabric/iq/ontology/how-to-use-ontology-graph
- Fabric Ontology REST API: https://learn.microsoft.com/rest/api/fabric/ontology/items

Because the service and item-definition formats remain preview/evolving, CEPIO v0.4 deliberately targets the stable semantic boundary rather than coupling CEPIO to a particular preview definition-generation layout.

## Binding bundle

`FabricIQBindingGenerator` produces two deterministic artifacts:

```text
ontology.ttl
binding-manifest.json
```

### `ontology.ttl`

A Fabric-importable ontology artifact containing the resolved CEPIO module closure:

- entity/class definitions;
- inheritance edges;
- object/relationship definitions;
- canonical datatype-property definitions;
- datatype ranges;
- deployment-profile property domains where explicitly bound.

N-Triples-compatible Turtle is emitted in sorted order so identical CEPIO inputs generate identical bytes.

### `binding-manifest.json`

A CEPIO-owned sidecar carrying semantics and deployment information that should not be encoded as Fabric-owned identity:

- requested CEPIO modules;
- dependency-resolved module set;
- module namespace + semantic version + tier + stability;
- canonical IRI for every entity, property and relationship;
- CEPIO property datatype mapped to the closest current Fabric ontology value type;
- static/time-series entity bindings;
- relationship source bindings;
- Fabric entity keys;
- canonical-contract SHA-256;
- generated ontology artifact SHA-256;
- ontology-managed Graph projection eligibility.

The manifest is the CEPIO-to-Fabric contract. Fabric-generated internal IDs are not canonical CEPIO identifiers.

## Reference Asset + Work binding

The first reference profile is:

```text
integrations/microsoft/fabric_iq/asset-work.bindings.yaml
```

Requested modules:

```text
asset
work_management
```

The generator automatically resolves their semantic dependencies:

```text
core
industrial
asset
work_management
```

The reference profile demonstrates:

```text
CEPIO industrial:Equipment
    -> Fabric Lakehouse equipment table
    -> key: asset:assetTag

CEPIO industrial:WorkOrder
    -> Fabric Warehouse work_orders table
    -> key: core:sourceId

CEPIO industrial:hasWorkOrder
    -> Fabric Lakehouse relationship table
    -> Equipment assetTag -> WorkOrder sourceId
```

Workspace and item identifiers in the reference profile are placeholders. The reference proves the binding contract offline; it does not require Fabric credentials.

## Supported source contract

The binding model recognizes the source families currently supported by Fabric Ontology preview:

- Lakehouse;
- Eventhouse;
- KQL database;
- Warehouse;
- SQL database;
- mirrored database;
- semantic model.

CEPIO distinguishes static entity bindings from time-series bindings. Static bindings require an entity key. Time-series bindings require a timestamp column.

Fabric currently constrains entity keys to string/integer properties, so the generator validates that CEPIO key properties map to a supported Fabric key type.

## Property semantics

CEPIO canonical datatype properties are intentionally reusable and are not universally assigned to one RDF domain in CEPIO-Core.

A customer/platform binding decides where a property is materially bound. For example:

```text
asset:assetTag
    CEPIO canonical property
       ↓ binding profile
industrial:Equipment
       ↓
Fabric Equipment.AssetTag
```

The generated Fabric TTL adds the deployment-specific `rdfs:domain` association only in the generated binding artifact. It does **not** modify CEPIO canonical ontology files.

This preserves the rule:

```text
CEPIO canonical meaning != customer/platform physical binding
```

## Graph

Fabric Ontology defines meaning; Fabric Graph materializes supported entity/relationship instances for graph traversal.

CEPIO therefore records graph projection as a separate capability in the manifest:

```text
CEPIO semantic relationship
        ↓
Fabric Ontology relationship
        ↓ optional materialization
Fabric Graph node / edge
        ↓
GQL / graph exploration
```

The manifest does not assume every ontology source is Graph-eligible. Current preview Graph support is narrower than Ontology data-binding support, and deployments must validate source eligibility before materialization.

CEPIO's own graph semantics and optional NVIDIA cuGraph analytics remain independent of Fabric Graph. Fabric Graph is one Microsoft-native execution/materialization binding.

## Drift detection

CEPIO can validate a TTL exported from Fabric against the binding manifest:

```python
report = generator.validate_exported_ttl(fabric_exported_ttl, manifest)
```

The validator detects:

- missing entity types;
- changed inheritance;
- missing datatype properties;
- changed datatype ranges;
- changed deployment-specific property domains;
- missing relationship types;
- changed relationship domains/ranges;
- additional Fabric-side semantic elements.

Additional Fabric-side elements are reported but do not, by themselves, make the canonical CEPIO contract nonconformant. Missing or changed canonical CEPIO semantics do.

## Generate the reference bundle

```bash
PYTHONPATH=src python scripts/generate_fabric_iq_binding.py
```

Default output:

```text
build/fabric-iq/asset-work/ontology.ttl
build/fabric-iq/asset-work/binding-manifest.json
```

Custom modules/profile:

```bash
PYTHONPATH=src python scripts/generate_fabric_iq_binding.py \
  --modules asset,work_management \
  --bindings integrations/microsoft/fabric_iq/asset-work.bindings.yaml \
  --output build/fabric-iq/asset-work
```

## Production deployment boundary

The v0.4 contract intentionally separates generation from deployment:

```text
CEPIO modules
     ↓
FabricIQBindingGenerator
     ↓
ontology.ttl + binding-manifest.json
     ↓
deployment adapter / CI-CD
     ↓
Fabric Ontology REST API / import surface
     ↓
Fabric Ontology
     ↓
OneLake / Lakehouse / Warehouse / Eventhouse / SQL / Semantic Model
     ↓
optional Fabric Graph
```

A future deployment adapter may translate the same manifest into the current Fabric Ontology REST item-definition format. That adapter belongs under `integrations/microsoft/*` and may evolve with Fabric preview APIs without changing CEPIO-Core or the binding manifest.

## Acceptance boundary for v0.4 P0

This integration is complete when:

1. Asset + Work Management render into a deterministic Fabric-importable artifact;
2. module/version/canonical IRI metadata is preserved in the sidecar manifest;
3. source binding contracts cover current Fabric ontology source families;
4. round-trip drift detection identifies missing or changed CEPIO semantics;
5. all tests run with no Fabric credential or service;
6. Fabric preview changes remain isolated to the Microsoft integration layer.
