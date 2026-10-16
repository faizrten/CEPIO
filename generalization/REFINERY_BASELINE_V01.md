# Refinery / Process-Manufacturing Baseline v0.1

## Purpose

This is CEPIO's second-archetype Generalization Lab baseline after drilling. The 16 business questions were frozen before the first run, and the ontology was not changed to improve the result.

## Raw baseline

- Archetype: `refinery-process-manufacturing-v0.1`
- Questions: 16
- PASS: 6
- PARTIAL: 5
- FAIL: 5
- ERROR: 0
- Raw semantic capability checks: **46.3%**
- Ontology hash at first run: `51fc018870553409`
- First CI run: `#578`

The raw result is retained as historical evidence and must not be rewritten after the fact.

## What generalized without refinery-specific remediation

The first run already passes reusable capabilities for:

- shift handover and unresolved-work continuity;
- equipment failure -> work-order reasoning and critical-spare context;
- permit / energy-isolation work control and verification;
- turnaround work packages, isolations, material requirements and contracted services;
- contracted-service execution, evidence, obligations and acceptance;
- reliability-driven turnaround work selection and procurement context;
- generic governed decision / approval and optimization-function patterns in questions where the surrounding domain semantics exist.

This is evidence that the common industrial operating layer is reusable beyond drilling.

## Benchmark-pattern errata discovered after the frozen run

Gap triage found several cases where the *business competency remains valid* but the v0.1 approved semantic pattern was not aligned to CEPIO's existing canonical vocabulary. These are benchmark-pattern defects, not evidence that CEPIO should add duplicate concepts.

Examples:

1. The pack references `process:ProcessUnit`; CEPIO already owns the canonical process-unit class as `industrial:ProcessUnit`.
2. The pack references `process:streamFeedsUnit`; CEPIO already represents process-stream topology with `process:streamFromUnit` and `process:streamToUnit`.
3. Some financial edges target the nonexistent `process:ProcessUnit`; the existing commercial relationships already accept the canonical `industrial:ProcessUnit` because it is a CEPIO Entity.
4. The manufacturing quality pattern references a generic `manufacturing:Specification`; CEPIO already has more precise ISA-95-aligned specification types such as `manufacturing:MaterialSpecification`. The remaining lot-to-quality-evidence semantics still require proper triage rather than a duplicate generic class.
5. Utility metering must not misuse `cepio:measuredBy` to point at a physical meter, because `measuredBy` ranges to a Measurement while `process:UtilityMeter` is Equipment. A corrected capability pattern or explicit meter/stream observation model is required.

## Interpretation rule

**46.3% is the raw frozen-v0.1 score, not the normalized cross-industry coverage score.**

The next frozen competency revision may correct approved semantic alternatives for the errata above, but it must keep the same business questions and may not hide genuine missing capabilities. Ontology remediation begins only after CORE / DOMAIN / PROFILE / MAPPING / REJECT triage.

## Genuine semantic areas exposed by v0.1

The first run indicates legitimate work is likely required around:

- process operating constraints;
- operating envelopes, operating limits and deviations;
- process-safety barriers and barrier impairment;
- management of change;
- product/lot quality evidence and disposition;
- emission limits and compliance evaluation;
- utility metering / utility-stream evidence and energy-intensity semantics;
- process-unit trip and production-loss semantics;
- startup / restart readiness.

Final ownership and vocabulary are decided by gap triage, not by this baseline report.
