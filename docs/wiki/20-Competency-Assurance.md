# Competency & Assurance

## Why competency matters to the North Star

The CEPIO North Star is **thin infrastructure, thick industrial intelligence**. That means product maturity cannot be measured by ontology size, number of connectors or quantity of runtime features alone.

The key question is:

> **How much real industrial work can CEPIO support through a stable, reusable and governed operating contract?**

Competency & Assurance is therefore a first-class product discipline and one of the primary ways CEPIO measures the thickness and quality of its Industry IQ.

## From model validity to industrial capability

```text
Ontology / schema validation
"Is the model structurally valid?"
              |
              v
Semantic competency
"Can CEPIO represent the required industrial capability?"
              |
              v
Runtime competency
"Can CEPIO retrieve evidence and execute permitted capabilities?"
              |
              v
Skill / procedural competency
"Can a bounded procedure perform the industrial task?"
              |
              v
Agent competency
"Can an AI system answer or recommend correctly from CEPIO evidence?"
              |
              v
Operational competency
"Can the governed loop produce and verify a real outcome?"
```

A domain is not mature simply because its classes and relationships validate.

## Persona-driven competency model

Competency should connect directly to target users and the decisions they make:

```text
Domain
  x
Persona
  x
Responsibility
  x
Decision
  x
Competency Question
  x
Required CEPIO Capability
```

The resulting acceptance chain is:

```text
Persona
  -> Job / responsibility
  -> Decision
  -> Competency question
  -> Evidence requirements
  -> Required semantics / Skill / Function / Decision / Action
  -> Assurance result
```

This is the bridge between **Target Users** and **Industry IQ Packs**.

## Example

A Reliability Engineer competency should not ask only whether `FailureMode` exists.

A stronger question is:

> Given increasing compressor vibration, previous failure history, current production exposure and outstanding maintenance work, should intervention occur now, and what evidence supports the recommendation?

That single competency pressures:

- equipment identity;
- `ConditionObservation`;
- temporal state;
- failure history;
- relationship traversal;
- `ProductionExposure`;
- work and maintenance context;
- provenance;
- uncertainty;
- Function execution;
- Decision capability;
- policy and authority;
- recommendation/action separation.

That is a measure of industrial intelligence, not vocabulary count.

## Current semantic evidence

| Artifact / stage | Scope | Documented result or checked-in expectation | Interpretation |
|---|---|---|---|
| Frozen drilling v0.1 baseline | 16 questions | 9 PASS / 7 PARTIAL; 84.7% semantic checks | Historical baseline |
| Same frozen v0.1 after remediation | Same 16 questions | 11 PASS / 5 PARTIAL; 94.6% semantic checks | Improvement against unchanged challenge |
| Drilling persona expansion v0.2, literal evaluation | 14 questions | 6 PASS / 8 PARTIAL; 64/74 semantic checks | Literal-prerequisite compatibility pack |
| Drilling persona capability pack v0.3 | 14 questions | 14 PASS; 100% deterministic semantic capability readiness | Approved semantic alternatives satisfy declared capabilities |
| Refinery persona expansion v0.2 | 12 expansion questions; 26-role catalog | Regression retains unresolved PARTIAL/FAIL pressure | No blanket readiness claim |

These packs use different evaluation contracts and denominators. They must not be presented as one simple linear percentage series.

## Why capability alternatives matter

The v0.3 drilling pack uses a `capability-alternatives` contract. CEPIO can satisfy a capability through an approved canonical semantic composition rather than copying the literal vocabulary of IADC, WITSML, OSDU, PPDM or another benchmark.

This is essential to the new North Star:

> **Thick industrial intelligence does not mean thick duplicated standards vocabulary.**

External standards challenge and inform CEPIO. They do not automatically become canonical CEPIO semantics.

## Current operational assurance

The drilling operational-assurance fixture has five deterministic gates with checked-in tests expecting 5 PASS / 0 FAIL / 0 ERROR:

1. **Temporal** — distinguish valid-time state from what CEPIO knew at different transaction times.
2. **Provenance** — trace a property through source record, observation time, mapping version and transformation run.
3. **Authority** — resolve a current holder through scoped authority assignment.
4. **Policy + kinetic** — reject execution by an AI recommender, allow an authorized human and preserve Decision-to-Action linkage.
5. **Operator evidence** — reject citations absent from the current evidence bundle.

These gates prove representative runtime behavior, not complete production readiness or end-to-end coverage of every competency question.

## Assurance maturity model

| Layer | Acceptance question | Product meaning |
|---|---|---|
| **Semantic** | Can approved concepts and relationships represent the capability? | Industry IQ can describe the work |
| **Runtime** | Can the actor retrieve and trace evidence and invoke permitted capabilities? | Industry IQ is executable against governed context |
| **Procedural / Skill** | Can a bounded Skill perform the required procedure? | Reusable industrial procedure exists |
| **Agent** | Can an agent answer/recommend correctly using authorized CEPIO evidence? | General intelligence can safely consume Industry IQ |
| **Operational** | Can the full loop produce a verified industrial outcome? | CEPIO supports real governed work |

Uncovered dimensions should remain `NOT_RUN` or explicitly uncovered rather than being inferred as passes.

## Competency as an Industry IQ Pack contract

Each Industry IQ Pack should increasingly declare:

- target domains;
- target personas;
- decisions supported;
- frozen competency questions;
- evidence requirements;
- required semantic compositions;
- Skills and Functions;
- Decision patterns;
- permitted Actions;
- policy/authority assumptions;
- runtime assurance gates;
- evaluation fixtures;
- known gaps and exclusions.

This makes an Industry IQ Pack testable rather than merely descriptive.

## Generalization and competency

Generalization and assurance use overlapping artifacts but answer different questions:

- **Generalization:** does the capability remain reusable across operating models, customers and platform bindings?
- **Assurance:** is the answer, recommendation or action actually justified by available evidence and authority?

Gap decisions remain:

`CORE / DOMAIN / MAPPING / PROFILE / REJECT`

The desired long-term pattern is:

```text
More domains and personas
        +
Higher competency coverage
        +
Fewer Core changes
        +
Fewer customer-specific exceptions
        =
Stronger reusable Industry IQ
```

## Platform-portability proof

Because CEPIO is portable Industrial Operating Intelligence, an important future competency test is:

> Can the same competency question, Skill and Decision contract behave consistently when enterprise context is supplied through different platform bindings?

For example:

```text
Fabric context ----+
                   |
Cognite context ---+--> same CEPIO competency / Skill / Decision
                   |
OSDU context ------+
```

The underlying evidence locations may differ. The industrial operating contract should remain stable.

## Product quality metric

A useful conceptual measure is:

```text
CEPIO maturity
=
Competency Coverage
x Runtime Capability
x Generalization
x Evidence Quality
x Governed Actionability
x Operational Reliability
```

This is not intended as a literal numerical score. It expresses the product principle that a zero in any critical dimension weakens the usefulness of the whole operating abstraction.

## Source contracts and regression expectations

- [Generalization harness](../generalization-harness.md)
- [Drilling semantic remediation](../drilling-semantic-remediation-v0.2.md)
- [Capability alternatives tests](../../tests/test_capability_harness_v03.py)
- [Refinery expansion tests](../../tests/test_refinery_persona_standards_expansion_v02.py)
- [Operational assurance contract](../../generalization/OPERATIONAL_ASSURANCE.md)
- [Operational assurance tests](../../tests/test_operational_assurance.py)

## Related documentation

- [Wiki home](Home.md)
- [Target Users / Personas](19-Target-Users-Personas.md)
- [Architecture](03-Architecture.md)
- [Roadmap](17-Roadmap.md)
