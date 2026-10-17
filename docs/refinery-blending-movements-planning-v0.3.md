# Refinery Blending, Movements and Planning v0.3

## Purpose

This slice adds the minimum source-neutral semantics needed to connect refinery/feed planning to executable tankage, blending and material-movement context without creating refinery-specific duplicates of existing ISA-95 manufacturing concepts.

## Canonical process-industry additions

- `process:CrudeAssay` — controlled feed-characterization information linked to a `process:MaterialStream`.
- `process:BlendPlan` — controlled blend intent tied to an existing manufacturing schedule and material lots.
- `process:MaterialMovement` — execution activity representing a bulk-material transfer.
- `process:TransferRoute` — source-neutral transfer-path identity used by movements.

Key relationships include:

- `process:characterizesStream`
- `process:blendPlanForSchedule`
- `process:blendPlanUsesLot`
- `process:movementFromStorage`
- `process:movementToStorage`
- `process:usesTransferRoute`
- `process:movementCarriesLot`
- `process:movementForSchedule`
- `process:routeFromStorage`
- `process:routeToStorage`

## Reused manufacturing semantics

CEPIO continues to reuse the ISA-95-aligned manufacturing identities for:

- `manufacturing:OperationsSchedule`
- `manufacturing:StorageUnit`
- `manufacturing:MaterialLot`

The process module therefore declares an explicit dependency on manufacturing rather than creating `process:StorageUnit`, `process:MaterialLot`, or `process:OperationsSchedule` aliases.

## Yield-model boundary

The accepted refinery v0.2 triage rejects `process:YieldModel` as a canonical class. A yield model is executable analytical content with implementation, version, parameters and runtime behavior. It is represented through `mappings/process_models.yaml` as a versioned `cepio:DigitalAsset` with semantic input/output bindings.

This keeps the ontology focused on durable operating context while allowing model registries, AI/ML systems and optimization engines to remain replaceable.

## Intended refinery reasoning chain

```text
Crude / feed stream
  -> Crude assay
  -> production schedule
  -> blend plan
  -> material lot
  -> storage unit
  -> material movement
  -> transfer route
  -> destination storage / process unit context
  -> inventory, quality and economic consequence
```

## Generalization guardrails

- The frozen refinery persona/standards competency pack v0.2 is not modified.
- No customer or site vocabulary is introduced.
- No tank-specific refinery class is introduced.
- Manufacturing remains the owner of generic storage, material-lot and schedule identities.
- Executable analytical models remain mapping/runtime-layer assets rather than ontology classes.

## Versioning

`process_industry` advances from `0.1.3` to `0.1.4`.
