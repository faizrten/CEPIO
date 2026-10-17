# Drilling-contractor domain qualification v0.4

## Scope and release boundary

This is a **domain qualification version**, not a CEPIO product release. It extends the v0.2 drilling-contractor persona set with seven enterprise, performance/optimization, contract, and digital/AI roles. The existing v0.1, v0.2, and v0.3 competency packs remain unchanged.

The frozen `drilling-contractor-domain-qualification-v0.4` pack contains nine operating-language questions in three challenge bands:

| Band | Questions | Challenge |
| --- | --- | --- |
| Enterprise | DC-DQ-001, DC-DQ-002, DC-DQ-006 | Fleet commitments, contract evidence, business objectives and risk |
| Operational optimization | DC-DQ-003, DC-DQ-004, DC-DQ-005 | Drilling performance forecasts, operating limits and consistent activity reporting |
| Agentic operations | DC-DQ-007, DC-DQ-008, DC-DQ-009 | Recommendations, control points, action cases, audit and approval evidence |

The questions use approved semantic alternatives rather than requiring one literal ontology path. The frozen pack fingerprint is `4c16efb2c64d5cf9bf70d9987c3693b20147dd89e3e8a2c48b0f82c2153fe05a`. Tests pin this fingerprint, exercise every added persona and band, and retain the initial semantic-pressure result.

## Initial baseline

Against the ontology at qualification, v0.4 records:

- 9 questions: 7 PASS, 1 PARTIAL, 1 FAIL;
- 9 of 11 semantic checks passing (81.8%);
- two classified CORE gaps, both in optimization semantics.

The unresolved gaps are intentional. A process forecast is not currently scoped to a drilling rig, and there is no supported composition connecting a rig-scoped operating constraint to an optimization decision. The accepted triage is in `generalization/gaps/drilling-contractor-domain-qualification-v0.4.yaml`. The gaps are evidence to classify, not a request to add terms or predicates until the score reaches 100%.

Agentic questions also declare runtime policy/provenance requirements. The semantic harness reports those runtime checks as `NOT_RUN`; they do not prove authorized execution or runtime lineage. Continue to use the separate drilling runtime coverage v0.5 contract for those claims.

## Qualification and remediation rules

1. Run the frozen pack with its persona expansion, standards registry and accepted gap triage. Keep the emitted batch hash, ontology hash, status counts and JSON report together.
2. Require the pack to remain frozen, all nine question IDs and all three bands to remain covered, every added persona to be referenced, and all persona/standard cross-references to resolve.
3. Assign every current PARTIAL/FAIL capability exactly one accepted disposition before ontology remediation:
   - **CORE** — reusable semantics with evidence beyond one drilling customer/domain;
   - **DOMAIN** — source-neutral drilling specialization;
   - **PROFILE** — customer, contractor, fleet or deployment-specific behavior;
   - **MAPPING** — external codes, taxonomy or source vocabulary to federate;
   - **REJECT** — the proposed pattern is redundant or semantically weaker than an existing abstraction.
4. Make any approved remediation in the appropriate ontology, profile or mapping layer, never by weakening the frozen questions or adding vocabulary solely to improve the score.
5. Update accepted gap triage in the same change as ontology remediation. The harness rejects missing, duplicate, or stale triage.
6. Preserve v0.4 and its historical reports. A materially changed question or alternative requires a new versioned pack and a new baseline; do not rewrite prior benchmark history.

The dedicated [drilling domain qualification workflow](../.github/workflows/drilling-domain-qualification.yml) runs the focused regression and harness and retains the JSON report as a CI artifact. It does not replace or weaken existing CI, quality, governance, or CodeQL workflows.

## Publication boundary

This benchmark is classified **PROTECTED — public abstraction only**. It contains no customer data and vendors no copyrighted standards text; the standards registry contains reference metadata and intended use only.
