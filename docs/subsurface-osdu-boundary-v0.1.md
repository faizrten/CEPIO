# CEPIO Subsurface OSDU / ADME Boundary v0.1

## Purpose

CEPIO Subsurface must not recreate OSDU or Azure Data Manager for Energy (ADME). OSDU/ADME is the governed technical data plane for subsurface domain data; CEPIO adds enterprise reasoning, uncertainty, decision provenance, governed action and cross-domain operating context.

The architecture rule is:

> **OSDU-first, extension-not-replication.**

Every external subsurface concept is classified as one of:

- **REUSE** — use the OSDU/DDMS object directly; CEPIO does not create a competing canonical payload.
- **BIND** — expose a thin CEPIO enterprise handle for navigation and cross-domain reasoning while preserving OSDU identity and authority.
- **EXTEND** — retain the OSDU object as authoritative and attach CEPIO epistemic/decision sidecars.
- **OWN** — use a CEPIO-native concept only for operating semantics that are not the responsibility of OSDU/DDMS.

The executable mapping contract is `mappings/osdu_subsurface_bindings.yaml`.

## Current platform baseline

Reviewed 2026-10-17.

ADME is currently aligned to the OSDU M26 milestone. The relevant managed domain services are:

- Seismic DDMS;
- Wellbore DDMS;
- Rock and Fluid Samples (RAFS) DDMS;
- Reservoir DDMS;
- External Data Services (EDS) for federated OSDU-compatible sources.

At the same baseline, Production DDMS and Well Delivery DDMS are not available as managed ADME services. Seismic DDMS v4 APIs, Energistics parser DAGs and Policy Service are also listed as unavailable. CEPIO therefore must resolve logical capabilities rather than hard-code a single ADME access path.

ADME Analytics Consumption Zone (ACZ) is also a partial analytics path during preview: catalog kinds and Wellbore DDMS kinds are supported, but Reservoir DDMS, Seismic Store DDMS and RAFS DDMS are not. CEPIO must not assume that all subsurface evidence can be materialized into Fabric through ACZ.

Official references:

- https://learn.microsoft.com/en-us/azure/energy-data-services/osdu-services-on-adme
- https://learn.microsoft.com/en-us/azure/energy-data-services/overview-ddms
- https://learn.microsoft.com/en-us/azure/energy-data-services/faq-energy-data-services
- https://learn.microsoft.com/en-us/azure/energy-data-services/tutorial-reservoir-ddms-apis

## Architectural boundary

```text
                         CEPIO
+-------------------------------------------------------+
| Enterprise semantics                                 |
| Evidence · Hypothesis · Assumption                   |
| Uncertainty · Confidence · Information Gain          |
| Decision provenance · Policy · Governed action       |
+---------------------------+---------------------------+
                            |
                  capability bindings
                            |
                            v
+-------------------------------------------------------+
|                OSDU / ADME DATA PLANE                 |
|                                                       |
| Core services                                         |
| Schema · Search · Storage · Dataset · Legal · Entitle |
|                                                       |
| DDMS                                                  |
| Wellbore · Seismic · RAFS · Reservoir                 |
|                                                       |
| Federation                                            |
| External Data Services                                |
+---------------------------+---------------------------+
                            |
                            v
      Petrel · Techlog · RMS · simulators · files
      acquisition systems · other OSDU platforms
```

## Why the CEPIO energy `Well` and `Reservoir` types remain

CEPIO already contains lightweight `energy:Well` and `energy:Reservoir` classes. They remain useful as **enterprise operating handles**, not as replacements for OSDU schemas.

The rule is:

```text
CEPIO energy:Well
    = stable enterprise navigation identity + operating relationships

OSDU master-data--Well
    = authoritative upstream technical record
```

CEPIO must not copy the full OSDU well or reservoir payload into the CEPIO canonical state. A binding preserves the OSDU record/version identity and adds only the minimum enterprise context needed for cross-domain relationships, decisions and policy.

## Object treatment matrix

| OSDU / DDMS concept | CEPIO treatment | Rationale |
|---|---|---|
| Well | BIND | Needed across drilling, production, projects, economics and decisions; technical payload remains OSDU. |
| Wellbore | REUSE | Domain-technical object; reference directly when needed. |
| Well log | REUSE | High-volume domain evidence; do not duplicate. |
| Trajectory | REUSE | Domain evidence; do not duplicate. |
| Well marker | REUSE | Domain evidence; do not duplicate. |
| Seismic dataset/volume | REUSE | Bulk data belongs in Seismic DDMS. |
| Reservoir | BIND | Stable enterprise context is useful; technical record remains OSDU. |
| Reservoir segment | REUSE | Technical subsurface segmentation remains OSDU. |
| Fault interpretation | EXTEND | OSDU owns the interpretation; CEPIO may attach hypothesis, confidence and uncertainty sidecars. |
| Stratigraphic interpretation | EXTEND | Same pattern as fault interpretation. |
| Fluid-boundary interpretation | EXTEND | Same pattern; often important to decision uncertainty. |
| Rock-fluid-unit interpretation | EXTEND | Same pattern. |
| Seismic 3D interpretation set | EXTEND | Interpretation remains OSDU; enterprise belief/authority can be attached in CEPIO. |
| Reservoir model scenario | EXTEND | OSDU owns scenario/model identity; CEPIO captures assumptions, evidence and decision relevance. |
| RESQML/grid/model payload | REUSE | Reservoir DDMS owns bulk/model representation. |
| Rock/fluid samples and analyses | REUSE | RAFS DDMS owns the records and reports; CEPIO uses them as evidence. |

## Epistemic sidecar pattern

CEPIO Core 0.3 introduces the semantic layer that OSDU objects can participate in without being copied.

Example:

```text
OSDU FaultInterpretation F12
          ^
          |
      assesses
          |
CEPIO UncertaintyAssessment UA-17
          |
          +---- supported/updated by ----> CEPIO Evidence E-44
          |                                  |
          |                                  +--> sourceRef: OSDU pressure/RFT data
          |
          +---- affects ----> CEPIO Hypothesis H-9
                                  "F12 is sealing"
```

The OSDU interpretation remains authoritative. CEPIO owns the organization's time-bound reasoning about that interpretation.

## Reservoir model scenario pattern

`ReservoirModelScenario` is not reimplemented in CEPIO.

Instead:

```text
OSDU ReservoirModelScenario RM-21
        |
        +--> referenced by CEPIO Evidence
        |
        +--> has CEPIO Assumptions
        |
        +--> has CEPIO UncertaintyAssessments
        |
        +--> informs a CEPIO/Kinetic Decision
```

This allows CEPIO to answer questions such as:

- Which assumptions were active when a well decision was made?
- Which uncertainty changed between model scenarios?
- What evidence caused confidence in a reservoir hypothesis to increase?
- Which decisions are exposed to one geological interpretation?
- What additional information would most reduce decision uncertainty?

without becoming a reservoir-model store or simulator.

## Uncertainty boundary

CEPIO owns the semantics of uncertainty but not the numerical engine.

### CEPIO owns

- what is uncertain;
- the subject of the assessment;
- epistemic vs aleatory classification where supplied by a domain profile;
- evidence and assumptions;
- confidence as a distinct assessment;
- dependencies and correlations;
- assessment history/supersession;
- information-gain semantics;
- decision relevance and provenance.

### External/domain engines own

- geomodel realization generation;
- reservoir simulation;
- Monte Carlo sampling;
- probability distribution fitting;
- Bayesian inference;
- uncertainty propagation;
- EVPI/EVSI calculation engines;
- specialized physics and optimization.

CEPIO records the meaning and provenance of the result and binds to the engine that produced it.

## Capability-based access

Applications and agents should request logical capabilities, for example:

```text
subsurface.wellbore.log
subsurface.seismic.dataset
subsurface.reservoir.model_scenario
subsurface.sample.analysis
subsurface.production.timeseries
```

A customer/platform profile resolves each capability to a concrete provider.

Example:

```yaml
subsurface.reservoir.model_scenario:
  preferred_binding: adme.reservoir_ddms

subsurface.production.timeseries:
  preferred_binding: null
  fallback_strategy: customer_profile_binding
```

This prevents CEPIO from treating current ADME product gaps as permanent ontology gaps.

## Anti-duplication invariants

The v0.1 contract requires that CEPIO:

1. never stores seismic bulk payloads as canonical CEPIO state;
2. never stores well-log bulk payloads as canonical CEPIO state;
3. never stores RESQML/grid bulk payloads as canonical CEPIO state;
4. never copies OSDU interpretation payloads into competing CEPIO canonical objects;
5. preserves OSDU record and version identity;
6. retains provenance on CEPIO epistemic sidecars;
7. does not assume ACZ supports every DDMS;
8. does not invent a CEPIO Production DDMS because ADME does not currently provide one.

## Reference decision loop

The first Subsurface reference scenario remains an infill-well decision:

```text
OSDU/ADME evidence
  wells · logs · seismic · interpretations · reservoir scenarios
                         |
                         v
CEPIO Evidence + Hypothesis + Uncertainty + Confidence
                         |
                         v
                 candidate opportunities
                         |
                         v
                    Decision
                         |
                         v
                     Action
                         |
                         v
                     Outcome
                         |
                         +----> new evidence / revised uncertainty
```

This scenario is broad enough to validate OSDU identity preservation, DDMS runtime binding, uncertainty provenance, decision reasoning and the learning loop without requiring CEPIO to duplicate subsurface technical data.

## Next implementation increment

v0.2 should implement the runtime abstraction behind the mapping contract:

1. `ExternalDomainReference` or equivalent source-reference contract without importing OSDU schemas into Core;
2. provider adapters for OSDU Core Search/Storage and ADME Wellbore/Reservoir DDMS reads;
3. evidence creation from authoritative OSDU references with source/version provenance;
4. one end-to-end scenario linking `ReservoirModelScenario -> Evidence -> UncertaintyAssessment -> Decision`;
5. customer-profile fallback binding for production time-series until a managed Production DDMS path is available.
