# Competency & Assurance

## First-class acceptance discipline

Competency & Assurance is a first-class concern in CEPIO's documentation. Structural ontology validation establishes model validity. Competency evaluation establishes whether declared semantic compositions support industrial questions. Operational assurance separately exercises evidence and governed runtime behavior.

The repository implements deterministic semantic and operational gates. Treating competency coverage as a primary release-quality measure across every persona and domain is the proposed direction; universal enforcement is not established by the inspected artifacts.

## Current semantic evidence

| Artifact / stage | Scope | Documented result or checked-in expectation | Interpretation |
|---|---|---|---|
| Frozen drilling v0.1 baseline | 16 questions | 9 PASS / 7 PARTIAL; 84.7% semantic checks | Historical baseline documented in remediation notes |
| Same frozen v0.1 after remediation | Same 16 questions | 11 PASS / 5 PARTIAL; 94.6% semantic checks | Regression contract against the unchanged challenge |
| Drilling persona expansion v0.2, literal evaluation | 14 questions | 6 PASS / 8 PARTIAL; 64/74 semantic checks | Separate literal-prerequisite pack retained for compatibility |
| Drilling persona capability pack v0.3 | 14 questions | 14 PASS; 100% deterministic semantic capability readiness | Approved semantic alternatives satisfy declared capability requirements |
| Refinery persona expansion v0.2 | 12 expansion questions; 26-role catalog | Regression expects remaining PARTIAL/FAIL results and a rate below 100% | Explicit remaining semantic pressure; no blanket readiness claim |

These are different packs and evaluation contracts. Their percentages must not be presented as a single directly comparable improvement series. Semantic-check pass rate and question PASS rate also have different denominators.

The v0.3 pack uses the harness's `capability-alternatives` contract. A capability can be satisfied by a complete approved composition instead of one literal vocabulary pattern. Pack v0.3, harness version and product release version are independent identifiers.

Approved alternatives preserve architectural discipline: external codes can remain mapped references; competency can be demonstrated through requirements, assessments and evidence; readiness can be derived from cross-domain facts. A certificate alone is not equivalent to demonstrated competence.

## Current operational assurance

The drilling operational-assurance v0.4 fixture has **five gates**, with checked-in tests expecting **5 PASS / 0 FAIL / 0 ERROR**:

1. **Temporal:** distinguish valid-time state from what CEPIO knew at different transaction times.
2. **Provenance:** trace a property through source record, observation time, mapping version and transformation run.
3. **Authority:** resolve a current holder through a scoped `AuthorityAssignment`.
4. **Policy + kinetic:** reject execution by an AI recommender, allow an authorized human, and preserve Decision-to-Action audit linkage.
5. **Operator evidence:** reject citations absent from the current evidence bundle.

The fixture references `DC-PC-001`, `DC-PC-002`, `DC-PC-004` and `DC-PC-005`. Five assurance gates do not mean five fully covered questions, and this fixture does not cover all 14 semantic questions end to end. It establishes representative runtime behavior in a deterministic scenario, not live industrial operation or production readiness.

## Executable Operator boundary

Operator v0.6 provides an executable agent boundary through governed CEPIO REST or MCP. Its planner interface is provider-neutral; CI uses deterministic planners. Successful tool results become immutable evidence records with deterministic IDs. An answered response must cite evidence from its current run; unknown citations are rejected. Insufficient evidence must produce `INSUFFICIENT_CEPIO_EVIDENCE`.

This establishes constrained access and citation discipline. Evidence-ID validation alone does not prove that every claim in an answer is entailed by the cited records. Broad live-model answer-quality evaluation, independent judging and adversarial coverage remain further assurance work.

## Assurance maturity model — design direction

The following five-layer model organizes future coverage; it is not a claim of complete implementation:

| Layer | Acceptance question | Current evidence boundary |
|---|---|---|
| Semantic | Can approved concepts and relationships represent the required capability? | Deterministic harness and frozen packs |
| Runtime | Can the actor retrieve and trace the required evidence and execute permitted capabilities? | Representative drilling assurance fixture and runtime tests |
| Procedural / Skill | Can a bounded procedure operate under its declared dependency and authority contract? | Skill binding/preflight slices; full persona coverage unestablished |
| Agent | Can an agent answer correctly using only authorized CEPIO evidence? | Executable Operator access/citation boundary; comprehensive answer correctness unestablished |
| Operational | Can the full governed loop produce a verified industrial outcome? | Reference workflow/verification implementations; live end-to-end qualification remains separate |

Future reporting should show persona, question/pack version, semantic result, runtime dimensions, Skill/agent evidence, policy outcomes and verified effects separately. Preserve `NOT_RUN` or uncovered status instead of counting missing execution as a pass. Record commit, fixture, input/ontology hashes and run evidence so results remain reproducible.

Generalization and assurance should share questions and evidence while preserving their different purposes: generalization tests reuse across operating models; assurance tests whether a claim is justified. Gap decisions remain `CORE / DOMAIN / MAPPING / PROFILE / REJECT`. Ontology growth alone is not a maturity measure.

## Source contracts and regression expectations

- [Generalization harness](../generalization-harness.md)
- [Drilling semantic remediation](../drilling-semantic-remediation-v0.2.md)
- [Capability alternatives tests](../../tests/test_capability_harness_v03.py)
- [Refinery expansion tests](../../tests/test_refinery_persona_standards_expansion_v02.py)
- [Operational assurance contract](../../generalization/OPERATIONAL_ASSURANCE.md)
- [Operational assurance tests](../../tests/test_operational_assurance.py)
- [Operator v0.6](../../generalization/OPERATOR_V06.md)

The counts above describe documented historical results or checked-in regression expectations at commit `d393bf0749922699ec4d22f7fd4833c8548702ed`. This documentation update does not report a fresh test run.


## Related documentation

- [Wiki home](Home.md)
- [Target Users / Personas](19-Target-Users-Personas.md)
- [Competency & Assurance](20-Competency-Assurance.md)
