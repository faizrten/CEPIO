# ADR-0022: Capability Registry and Compounding Industrial Intelligence

- Status: Proposed
- Date: 2026-10-19

## Context

CEPIO Domain Onboarding now produces frozen competency, semantic and runtime-evidence results and stops at `GENERALIZATION_REVIEW`. Without a governed post-onboarding mechanism, reusable discoveries can remain trapped in domain packs or be promoted informally, making CEPIO larger without proving that it is becoming more general.

CEPIO also already has two runtime registries with distinct responsibilities: the Industry IQ Pack Registry for deployable functions/decisions/actions and the Skill Registry for resolved Skill execution admission. A compounding mechanism must not duplicate either one.

The project requires a strict customer boundary: customer data and customer-specific profile semantics must not train or silently redefine global CEPIO knowledge.

## Decision

Introduce an evidence-backed **Capability Registry** as the ledger of what CEPIO can reliably claim it knows how to do.

A global capability record may reference source-neutral semantic, competency and runtime evidence, validated domains, maturity, reasoning/Skill context, runtime binding patterns and promotion provenance. `CORE`, `COMMON` and `DOMAIN` records must reject customer-specific or profile-scoped evidence and direct `/customers/` artifact references.

Introduce `workflow.capability-promotion.v1` and `cepio-capability-promotion-policy` with these invariants:

1. promotion to reusable `CORE`/`COMMON` requires at least two independent domains;
2. the configured cross-domain regression suite must survive at 100%;
3. customer-specific evidence cannot justify global promotion;
4. architecture approval must be supplied by a human-reviewed decision artifact; AI/agent roles cannot approve;
5. the automation emits a proposed registry snapshot but does not overwrite a committed registry version;
6. domain release remains a separate human review gate.

The first regression suite covers independent Drilling Contractor and Refinery qualification evidence. The initial registry backfills only `industrial.reliability.condition-work-context`, because the same reusable condition/equipment/work pattern is already qualified in both domains semantically and at runtime.

The existing `CEPIO Domain Onboarding` GitHub workflow becomes the single control-plane entry point. After Domain Onboarding, it runs the compounding loop and publishes onboarding, compounding and proposed-registry evidence.

## Consequences

### Positive

- every domain run can contribute reusable, auditable industrial capability;
- promotion is evidence-driven and regression-protected rather than vocabulary-driven;
- capability claims record where they have been proven and at what maturity;
- later domains can measure semantic and competency reuse against prior qualified capability;
- customer isolation is enforced at the registry contract boundary;
- Industry IQ Studio can later visualize the same registry and workflow without inventing another model.

### Costs

- reusable capability promotion now requires explicit evidence and human review;
- regression suites must expand as new independent domains become qualified;
- v0.1 human decision artifacts are source-controlled but are not yet identity-bound to CEPIO Authority/Entra records.

## Rejected alternatives

### Treat the ontology as the compounding memory

Rejected. Ontology terms do not encode competency, evidence, maturity, validated domains, reasoning patterns or regression provenance.

### Reuse the Industry IQ Pack Registry

Rejected. Pack installation answers what runtime packages are available, not what industrial capability CEPIO has proven across domains.

### Learn directly from customer data

Rejected. It violates the customer-isolation principle and confuses deployment-specific evidence with reusable industrial abstraction.

### Automatically promote after two matching domains

Rejected. Recurrence is evidence for review, not permission to change the global abstraction. Human architecture judgment and regression survival remain mandatory.

## Validation

The implementation must pass:

- full CEPIO CI, CodeQL, governance and quality gates;
- 100% statement coverage for the new `capability_registry.py` contract surface;
- the real Drilling + Refinery cross-domain regression suite;
- the Refinery compounding canary, expected to reach `READY_FOR_RELEASE_REVIEW` with no automatic release;
- customer-specific evidence rejection and AI/agent approval rejection tests.

Existing gates remain enforced; no quality, governance, ontology compatibility or release control is removed or weakened.
