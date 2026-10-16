# Drilling Persona Expansion Gap Triage — v0.2

## Purpose

The drilling-contractor persona expansion deliberately widened the Generalization & Competency Harness from 10 to 24 personas without changing the canonical ontology. The frozen expansion pack contains 14 additional competency questions and established the following baseline against CEPIO after the first drilling remediation cycle:

- 14 questions;
- 2 PASS / 12 PARTIAL;
- 0 FAIL / 0 ERROR;
- 49 of 74 deterministic semantic checks passing;
- **66.2% semantic coverage**.

This document records the architecture response to those gaps. It does not remediate the ontology.

## Classification result

| Disposition | Decisions | Meaning in this triage |
|---|---:|---|
| CORE | 6 | Reusable semantics that should apply beyond drilling. |
| DOMAIN | 3 | Genuine source-neutral drilling/offshore specializations. |
| PROFILE | 0 | No evidence that any discovered gap is customer-specific. |
| MAPPING | 0 | No new external codeset/taxonomy gap was exposed by this persona slice. |
| REJECT | 8 | The competency is valid, but the literal proposed semantic should be replaced by a better abstraction. |

The accepted machine-readable decisions are in `generalization/gaps/drilling-contractor-persona-v0.2.yaml`.

## CORE candidates

### Authority assignment

`DC-PE-001` and `DC-PE-010` independently expose the need to represent who holds bounded operational authority. CEPIO should not infer authority solely from a job title. A reusable `AuthorityAssignment` should capture the holder, scope, validity and asset or operating boundary.

### Shift handover

`DC-PE-003` demonstrates a reusable need for shift/tour handover semantics. The object should carry unresolved work, hazards and state across personnel changes and should generalize to process plants, mines and utilities.

### Energy isolation

`DC-PE-006` exposes a common HSE requirement for explicit energy isolation linked to the affected asset and governing permit/work.

### Crew rotation

`DC-PE-012` demonstrates that rotation is different from assignment: rotation expresses planned workforce transition across time and is relevant to offshore and other remote industrial operations.

### Purchase order

`DC-PE-014` exposes a missing common supply-chain execution concept needed to connect requirements, suppliers, commitments and delivery risk.

## DOMAIN candidates

### Drilling-fluid observation

`DC-PE-008` supports a source-neutral drilling-domain measurement specialization for fluid properties and operating-envelope observations. The benchmark's drilling-only `observationForActivity` predicate is rejected because CEPIO already has common measurement relationships.

### Cementing

`DC-PE-009` supports `CementingJob` and `CementProgram` as drilling-domain concepts. Service-delivery evidence is deliberately kept out of the drilling ontology because the same evidence/acceptance pattern applies to many contracted services.

### Marine support asset

`DC-PE-013` supports a conservative drilling/offshore `MarineSupportAsset` specialization for rig-move planning. The dedicated `supportedByMarineAsset` predicate is rejected in favor of existing generic dependency semantics until stronger cross-domain evidence appears.

## Rejected literal proposals

The harness exposed several questions where the operational need is real but the literal semantic proposal would weaken the ontology:

- direct `CrewMember -> assignedToActivity` loses role, shift and validity context; use `CrewAssignment`;
- direct `CrewMember -> responsibleForWork` loses responsibility scope and temporal context; use a reusable responsibility-assignment pattern;
- drilling-only service-provider/evidence semantics fragment a cross-industry service-delivery boundary;
- drilling-only observation/activity predicates duplicate common measurement semantics;
- drilling-only `ProgramDeviation` is too narrow; deviations should be common operational-plan semantics;
- stored `MobilizationConstraint` repeats the earlier readiness-constraint anti-pattern and should be derived from underlying evidence;
- drilling-only marine-support predicates duplicate common dependency semantics.

## Architectural significance

The 66.2% score should not be interpreted as an ontology-quality failure. The wider persona set is doing what the harness is designed to do: expose where CEPIO is still biased toward management-level asset/maintenance semantics and where it needs stronger operating abstractions for authority, workforce continuity, service boundaries, frontline work and enterprise support functions.

The key positive signal is that **none of the 12 PARTIAL questions require customer-profile vocabulary**. The pressure is primarily toward reusable operating semantics and a small number of legitimate drilling-domain specializations.

## Next remediation order

The recommended implementation order is:

1. common authority/responsibility assignment pattern;
2. common shift handover and crew rotation;
3. common HSE energy isolation;
4. common service-delivery/provider/evidence/acceptance pattern;
5. common purchase-order semantics;
6. drilling-fluid observation;
7. cementing job/program;
8. marine support asset;
9. revise future frozen questions where the literal benchmark proposal was rejected.

No customer profile changes are required for this remediation slice.
