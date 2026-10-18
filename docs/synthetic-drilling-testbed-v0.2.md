# Synthetic Drilling Testbed v0.2 — Multimodal Extension

## Purpose

Drilling v0.2 extends the v0.1 CEPIO MVP conformance fixture from heterogeneous structured data into multimodal industrial evidence. The four v0.1 scenarios remain unchanged so failures in v0.2 can be attributed to multimodal binding rather than changed domain ground truth.

## New coverage

v0.2 adds five modalities:

1. synthetic Daily Drilling Reports and inspection reports;
2. deterministic raster inspection images;
3. engineering-context SVG diagrams;
4. GeoJSON rig, well and rig-move context;
5. 2,048 Hz reference high-frequency waveform data.

Together with the v0.1 baseline, the testbed now covers structured/tabular records, low-frequency telemetry, temporal events, semantic graph relationships, documents, images, diagrams, geospatial data and high-frequency signals.

## Architectural boundary

Raw multimodal payloads remain source-native. CEPIO is responsible for binding each artifact to canonical identity, scenario/event context, valid time and provenance. The ontology should represent the meaning and relationships of evidence, not serialize large files or signal arrays into RDF triples.

Every generated multimodal artifact therefore carries:

- a deterministic artifact ID;
- modality and MIME type;
- canonical CEPIO asset IRI;
- source equipment ID;
- scenario ID;
- event time;
<<<<<<< HEAD
- explicit synthetic ground-truth claims;
=======
- explicit ground-truth claims;
>>>>>>> origin/main
- generator provenance.

## Acceptance gate

<<<<<<< HEAD
The v0.2 deterministic conformance gate preserves all twenty v0.1 golden questions and adds ten multimodal questions covering document corroboration, visual evidence, diagram grounding, geospatial relationships, waveform evidence, cross-modal fusion, source-native artifact references and multimodal provenance.

The immediate runtime objective is to make REST, Python SDK and MCP answer the same 30 fixture questions from the same CEPIO semantic contract without application code needing to understand the source formats.

This public conformance gate must not be confused with the live Agent Challenge qualification evaluator. Public fixture questions and deterministic answers are intentionally reproducible; a real model benchmark requires an evaluator that is not distributed in the public repository.
=======
The v0.2 gate preserves all twenty v0.1 golden questions and adds ten multimodal questions covering document corroboration, visual evidence, diagram grounding, geospatial relationships, waveform evidence, cross-modal fusion, source-native artifact references and multimodal provenance.

The immediate runtime objective is to make REST, Python SDK and MCP answer the same 30 questions from the same CEPIO semantic contract without application code needing to understand the source formats.
>>>>>>> origin/main

## Future modalities

Video, acoustic WAV, thermal imagery, 3D/OpenUSD, historian quality semantics and machine/controller logs remain candidates for later fixture revisions. They should be added only after the v0.2 evidence-binding model is proven stable.
