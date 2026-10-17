# CEPIO Synthetic Industrial Dataset — Drilling v0.2 Multimodal

v0.2 extends the v0.1 drilling conformance fixture without changing its four ground-truth scenarios. The objective is to test whether CEPIO can bind heterogeneous industrial evidence to the same canonical object/event graph while preserving source-native payloads.

## Added modalities

- **Documents** — synthetic Daily Drilling Reports and inspection reports in Markdown.
- **Inspection images** — deterministic PPM P3 raster fixtures with known visual features.
- **Engineering diagrams** — deterministic SVG equipment/context schematics.
- **Geospatial** — GeoJSON rig, well and synthetic rig-move context.
- **High-frequency signals** — per-scenario waveform CSVs at a 2,048 Hz reference sampling rate.

v0.1 structured/tabular, low-frequency telemetry, event/temporal and graph semantics remain the baseline.

## Generate

```bash
python scripts/extend_drilling_mvp_multimodal_v02.py \
  --output .generated/drilling-v0.2 \
  --telemetry-points 12000 \
  --waveform-samples 4096
```

Generated payloads stay under `.generated/` and are not committed. The fixture contract, expected modality bindings and 30 golden questions are committed.

## Architectural rule

CEPIO does **not** serialize large source artifacts into the ontology. It stores semantic identity, relationship, temporal and provenance bindings while the original artifact remains source-native and addressable by reference.

## Acceptance sequence

1. Run all v0.1 conformance tests unchanged.
2. Generate v0.2 deterministically.
3. Validate all required modalities and artifact metadata.
4. Resolve each artifact to the correct canonical asset and scenario.
5. Run all 30 golden questions across REST/SDK/MCP.
6. Require source provenance for every multimodal answer.
