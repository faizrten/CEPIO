# Drilling Harness Semantic Remediation — v0.2

## Purpose

This change is the first remediation cycle driven by the CEPIO Generalization & Competency Harness. It keeps the frozen `drilling-contractor-v0.1` competency pack unchanged and implements only the semantic changes accepted by the v0.1 gap classifier.

The baseline challenge scored:

- 16 competency questions;
- 9 PASS / 7 PARTIAL;
- 84.7% deterministic semantic checks.

The remediation regression contract is:

- 11 PASS / 5 PARTIAL;
- 94.6% deterministic semantic checks;
- no change to the frozen competency questions;
- remaining PARTIAL results must be explicitly triaged rather than silently filled with new vocabulary.

## Implemented drilling-domain semantics

### Drilling report and activity

CEPIO now includes source-neutral concepts for:

- `drill:DrillingReport`;
- `drill:DailyDrillingReport`;
- `drill:ActivityInterval`;
- `drill:DrillingActivityClassification`;
- report -> rig / well / activity relationships;
- activity -> rig / well / classification relationships.

`cepio:startTime` and `cepio:endTime` provide the temporal interval properties rather than introducing drilling-specific duplicates.

### IADC DDR Plus and WITSML classification boundary

`mappings/drilling_activity_classifications.yaml` defines federation semantics for IADC DDR Plus and WITSML. External activity codes remain external identifiers/codesets with source provenance. They are not copied into the CEPIO canonical class hierarchy.

This is why the frozen v0.1 question that literally asks for `drill:ActivityCode` remains PARTIAL even though the architectural need is now addressed correctly.

### Well-control assurance

CEPIO now includes:

- `drill:WellControlEquipmentSystem`;
- `drill:BlowoutPreventer` as drilling equipment;
- `drill:WellControlTest` as an industrial inspection;
- rig -> well-control system/equipment relationships;
- well-control test -> tested equipment relationship.

The model reuses the common industrial asset and inspection abstractions rather than creating a parallel drilling-only maintenance model.

### Jack-up mobility and readiness

CEPIO now includes:

- `drill:JackUpRig`;
- `drill:JackUpMove`;
- `drill:PreloadAssessment`;
- `drill:PunchThroughRisk`;
- move -> rig;
- preload assessment -> move;
- move -> punch-through risk.

These are source-neutral drilling-domain concepts and are not tied to ARO or another customer profile.

## Implemented common workforce semantics

The workforce module now includes `wf:CompetencyRequirement` plus relationships for:

- crew assignment -> required competency;
- competency assessment -> requirement;
- competency evidence -> requirement.

CEPIO deliberately does **not** add `Certification -> meetsCompetencyRequirement`. A certificate can be evidence relevant to competence, but certification is not logically equivalent to demonstrated competence.

## Implemented common commercial semantics

The commercial module now includes:

- `comm:ContractRate`;
- `comm:RateBasis`;
- `comm:rateForContract`;
- `comm:hasRateBasis`.

A rate can use existing common properties such as `comm:amount`, `comm:currency`, `cepio:validFrom` and `cepio:validTo`.

CEPIO already contains the legacy/common scalar `comm:dayRate`; it is retained for backward compatibility. The remediation does **not** add the frozen benchmark's proposed `drill:dayRate` property.

## Deliberately unresolved literal gaps

The remaining v0.1 PARTIAL results are intentional:

| Competency | Literal missing semantic | Decision |
|---|---|---|
| DC-CQ-003 | `drill:NonProductiveTimeEvent` | Reject the event type; derive NPT from activity/productivity classification plus causal downtime/failure. |
| DC-CQ-004 | `drill:ActivityCode` and `classifiedByActivityCode` | External classification mapping/federation, not a copied canonical codeset. |
| DC-CQ-005 | `Certification -> meetsCompetencyRequirement` | Reject equivalence; use assessment/evidence against competency requirements. |
| DC-CQ-009 | `drill:dayRate` | Reject drilling-only scalar; use common commercial rate semantics while retaining existing `comm:dayRate` compatibility. |
| DC-CQ-013 | `drill:CampaignReadinessConstraint` | Reject stored drilling class; derive readiness from workforce, supply, HSE and contract evidence through governed reasoning. |

The current unresolved decisions remain in `generalization/gaps/drilling-contractor-v0.1.yaml`. Implemented historical decisions move to `generalization/gaps/drilling-contractor-v0.1-resolutions.yaml`.

## Versioning

The changes are additive and source-neutral. The affected modules move from `0.1.0` to `0.1.1`:

- drilling;
- workforce;
- commercial.

No previously accepted class, relationship or datatype property is removed.

## External grounding

The design is challenged against public/reference surfaces from IADC DDR Plus, IADC KSA, IADC Model Contracts, IADC jack-up guidance, Energistics WITSML, API Standard 53 and API RP 2JU. CEPIO stores references and mapping intent, not copyrighted standards content.

## Next harness step

Semantic readiness remains distinct from runtime evidence. Temporal/provenance questions in the frozen pack still report `NOT_RUN`; the next runtime-evidence slice should create deterministic drilling scenario fixtures and evidence bundles before introducing a live Operator LLM into CI.
