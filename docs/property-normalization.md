# SEO + AD property-level normalization

## Purpose

The entity-level normalization established which concepts belong in CEPIO Core, Industrial Common, Process Industry/EPCIC, Drilling, or customer profiles. This track applies the same discipline to source properties.

A source column is **not automatically a canonical ontology property**. Each property occurrence is classified as one of five semantic roles:

1. `canonical-property` — a reusable CEPIO datatype property;
2. `relationship-key` — a source-system foreign key that should resolve to an object relationship rather than survive as a semantic attribute;
3. `observation-value` — a measured/derived value whose metric and time context must be retained;
4. `observation-timestamp` — event/measurement time;
5. `profile-property` — customer/domain-specific semantics retained explicitly until reuse justifies promotion.

## Coverage

The generated mapping covers every source property occurrence in the supplied reference packages:

- SEO: 441 property occurrences across 42 entity types;
- AD: 526 property occurrences across 59 core entity types;
- total: 967 classified property mappings.

## Canonical property contract

Every canonical datatype property declares QName/full IRI, canonical datatype, and write/semantic authority (`source-system`, `domain`, `derived`, `system`, or `governed-action`). Source mappings also carry temporal semantics, unit strategy, provenance strategy, relationship target or observation metric as applicable.

## Key design examples

- `SEO.WorkOrder.EquipmentId` is a `relationship-key`, not an enduring CEPIO string property.
- `SEO.Site.MaxTempC` and `SEO.UtilityMeter.Flow` are observations, not slowly changing asset attributes.
- `SourceSystem`, `LoadedAt`, AD `sourceTable`, and `sourceMeasure` are provenance metadata.
- ARO/REI-specific scores and SATORP-specific fields remain explicit profile semantics until reuse justifies promotion.

## Promotion rule

Promote a profile property into a CEPIO common/domain module when it is independently reused, defined by an accepted standard, required by a canonical action/function contract, or required for cross-domain reasoning with stable semantics.

## Generated mapping corpus

The complete 967-row generated mapping corpus was produced from the two supplied reference packages. The repository carries the canonical vocabulary, representative examples, summary and cryptographic manifest. The full generated CSV outputs are retained as a build artifact rather than treated as hand-maintained source-of-truth; their hashes are recorded in `mappings/property_mapping_manifest.json`.
