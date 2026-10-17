# Refinery Electrical and Asset Management v0.5

## Purpose

This slice closes the reusable refinery gaps around electrical equipment identity and ISO-55001-style asset decision context without copying IEEE assessment methods or refinery-specific electrical structures into the canonical ontology.

## Canonical industrial additions

- `industrial:ElectricalEquipment` — reusable electrical equipment category.
- `industrial:ElectricMotor` — electric motor identity, specialized from both rotating and electrical equipment.
- `industrial:MotorControlCenter` — reusable MCC identity.
- `industrial:drivesEquipment` — links a motor to driven equipment.
- `industrial:suppliesPowerTo` — links electrical equipment to supplied equipment.

These concepts live in `industrial` because they recur across refining, chemicals, upstream, power, mining and manufacturing.

## Canonical asset-management additions

- `asset:AssetCriticality` — an assessed criticality value modeled as `cepio:Measurement`, not a static label.
- `asset:AssetManagementPlan` — controlled lifecycle planning content modeled as `cepio:Document`.

Key relationships:

- `asset:criticalityForAsset`
- `asset:planForAsset`
- `asset:criticalityInformsPlan`
- `asset:planAddressesRisk`
- `asset:planTracksKPI`

This creates a reusable decision chain:

```text
Asset
  -> Asset Criticality
  -> Asset Management Plan
  -> Risk / KPI context
  -> Decision / intervention
```

The asset module does not acquire a dependency on the kinetic layer. Decisions continue to use CEPIO's existing foundation semantics and generic `cepio:impacts` relationship.

## Electrical operating chain

```text
Motor Control Center / Electrical Equipment
  -> supplies power to
Electric Motor
  -> drives
Pump / Compressor / Equipment
  -> contributes to
Process Unit availability and production
```

Electrical hierarchy can also compose existing `asset:AssetSystem`, `asset:FunctionalLocation`, `asset:installedAt` and `asset:hasSystem` semantics.

## IEEE 1584 boundary

The frozen refinery benchmark asks for `hse:ArcFlashStudy`, but the accepted gap triage rejected a dedicated ontology class. Arc-flash is an assessment method and study artifact rather than a new kind of HSE business object.

`mappings/electrical_asset_management_bindings.yaml` therefore maps:

```text
IEEE 1584 ArcFlashStudy
  -> hse:RiskAssessment
  -> cepio:impacts
  -> industrial:ElectricalEquipment
```

Incident energy, arc-flash boundary values and related engineering results remain measurements/properties with provenance. The calculation method remains external mapping metadata.

## IEEE 841 boundary

IEEE 841 qualification and motor-rating detail enrich a canonical `industrial:ElectricMotor`. CEPIO does not create IEEE-specific motor subclasses for every standard, enclosure, rating or duty category.

## ISO 55001 boundary

CEPIO canonicalizes the durable decision concepts needed across asset-heavy industries: assessed criticality and an asset-management plan. Scoring methodologies, organization-specific criticality matrices and plan templates remain external mappings or enterprise/profile content.

## Generalization guardrails

- Frozen refinery competency pack v0.2 remains unchanged.
- No refinery-specific electrical asset hierarchy is introduced.
- No `hse:ArcFlashStudy` class is introduced.
- No benchmark-only `ElectricMotor -> cepio:partOf -> Equipment` assertion is introduced.
- Industrial and asset modules remain industrial-common and independent of `process_industry`.
- No customer/profile vocabulary is introduced.

## Frozen benchmark result

Measured by CI after implementation:

- `RP-PE-006`: 3/7 -> 6/7 PARTIAL
- `RP-PE-009`: 5/7 -> 7/7 PASS
- aggregate: 67/87 (77.0%) -> **72/87 (82.8%)**
- status: **PASS 6 / PARTIAL 6 / FAIL 0 / ERROR 0**

The measured result exceeded the pre-CI forecast. The canonical `ElectricMotor` subclass hierarchy satisfied the equipment-identity semantic check without introducing the rejected benchmark-only `ElectricMotor -> cepio:partOf -> Equipment` assertion. The only remaining literal in `RP-PE-006` is `hse:ArcFlashStudy`, which intentionally remains represented through the IEEE 1584 risk-assessment mapping boundary.

## Versioning

- `industrial`: 0.2.1 -> 0.2.2
- `asset`: 0.1.0 -> 0.1.1
