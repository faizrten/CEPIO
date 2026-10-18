# Drilling CONNECT v0.5 — Binding Parity Proof

## Purpose

This milestone proves the new CEPIO North Star boundary for the Drilling Contractor domain:

> Thin Core, thick Industry IQ, replaceable authoritative bindings.

The same `cepio.iq.drilling.npt` Industry IQ capability must produce the same industrial meaning when its evidence comes from different platform bindings.

This is a **CONNECT** proof. It is not a live Microsoft Fabric connectivity claim.

## Architecture

```text
Synthetic evidence ──► SyntheticDrillingNPTBinding ──┐
                                                     │
                                                     ▼
                                             Drilling NPT evidence
                                              projection contract
                                                     │
Microsoft Fabric-shaped rows ─► Fabric binding ──────┘
                                                     │
                                                     ▼
                                            CEPIO runtime context
                                                     │
                                                     ▼
                                         Drilling NPT Industry IQ
                                         calculateNPTDuration
                                                     │
                                                     ▼
                                             semantic result
```

The generic Platform Binding seam remains provider-neutral. Drilling interpretation remains in Industry IQ. Fabric table shape remains inside the Fabric binding.

## Provider-neutral drilling evidence projection

The CONNECT proof resolves only the evidence required by the existing NPT capability:

- Operating Rig identity;
- Well identity;
- ActivityInterval identity and start/end time;
- DrillingActivityClassification identity;
- normalized `isProductive` meaning;
- immutable source record identity and version for every resolved evidence record.

The projection does **not** copy bulk telemetry, raw rig payloads, WITSML documents or provider-specific schemas into CEPIO.

## Bindings

### SyntheticDrillingNPTBinding

Acts as the deterministic control provider. It resolves the same thin drilling evidence contract from CEPIO-authored synthetic fixtures.

### FabricDrillingNPTBinding

Resolves normalized Fabric-shaped rows through a narrow `FabricDrillingNPTTableReader` transport seam. The first proof uses an in-memory reader in CI. A live authenticated Fabric transport can implement the same reader later without changing Drilling Industry IQ.

Normalized table boundaries used by the proof:

- `cepio_drilling_npt_context`
- `cepio_drilling_activity_interval`
- `cepio_drilling_activity_classification`

These are binding-layer contracts, not canonical CEPIO ontology tables.

## Equivalence gate

For the same industrial scenario, Synthetic and Fabric bindings must produce:

- the same canonical rig/well/activity/classification identifiers;
- the same activity time intervals;
- the same normalized productivity semantics;
- the same `calculateNPTDuration` result;
- the same provider-independent semantic signature.

Source record IDs, source systems, versions and dataset metadata are expected to differ and must remain preserved as provenance.

## Fail-closed qualification

The binding proof rejects:

- missing drilling context;
- duplicate context rows;
- missing activity evidence;
- missing activity classification;
- conflicting duplicate classifications;
- non-boolean normalized productivity meaning;
- missing source record version;
- source-system mismatch;
- context identity drift;
- evidence-only bindings exposing a governed write path through the generic Platform Binding conformance contract.

## North Star invariants

1. No Fabric business semantics are added to CEPIO Core.
2. No new drilling ontology term is introduced for this integration proof.
3. NPT remains a derived Industry IQ interpretation, not a canonical NPT event.
4. Platform bindings resolve evidence; they do not own industrial reasoning.
5. Evidence-only bindings are side-effect free.
6. Provider provenance is preserved but excluded from semantic parity hashing.
7. Bulk source payloads remain in the authoritative platform.

## Acceptance criteria

The milestone is qualified when:

- both bindings pass the generic evidence-binding conformance contract;
- Synthetic and Fabric NPT assessments are identical;
- semantic signatures are identical;
- provenance is complete and provider-specific;
- bulk/raw fields do not cross the evidence projection;
- all negative tests fail closed;
- existing CEPIO qualification and governance gates remain green.

## Next increment

After this parity proof is green:

1. replace the in-memory Fabric reader with a live authenticated Fabric transport in the Azure DEV environment;
2. keep the exact same binding and Drilling Industry IQ contracts;
3. add OSDU/ADME as the second materially different authoritative binding;
4. re-run provider parity and failure-mode qualification;
5. move from CONNECT to the governed EXECUTE loop for `CreateNPTInvestigation`.
