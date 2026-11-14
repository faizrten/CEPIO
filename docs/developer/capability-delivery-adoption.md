# Capability delivery adoption map

**Status:** Advisory engineering adoption, 14 November 2026. This map identifies reuse and evidence work; it does not qualify a runtime, deploy a feature, change a release gate, or increase the maturity score.

## Outcome and authority

Deliver reusable industrial capabilities that professionals can use and reviewers can verify, with less rework and founder intervention. Apply the [Agent Delivery Protocol](agent-delivery-protocol.md) through the existing [North Star](../strategy/industry-iq-product-north-star.md), contracts and repository controls. The protocol owns delivery guidance; focused contracts own behavior; the [roadmap](../roadmap.md), [current state](../current-state.md) and release manifest own their respective claims.

This reconciliation inspected Core `ac30abb8f8dc04abb917df74230f07ea23581ee4`. Existing source and documentation establish foundations, not proof that every deployed composition satisfies them. Protected evaluation findings belong in Labs and customer evidence stays in its authorized environment.

## Reuse and remaining proof

| Area | Existing authoritative home | Adopt or adapt | Remaining proof / responsible workstream |
| --- | --- | --- | --- |
| Delivery | [Agent Delivery Protocol](agent-delivery-protocol.md) | Complete slices, explicit dependencies, exact symptom reproduction and separate completion evidence | Core engineering: apply to representative changes and measure rework; this document alone is not effectiveness evidence |
| Architecture | [Architecture](../architecture.md), [Binding Contract](platform-bindings.md) | Small usable interfaces, localize complexity, reuse real variation points | Core reviewers: identify concrete interface friction before proposing refactors; preserve auth/provenance boundaries even when wrappers look thin |
| Capability ownership | [Capability Registry](../capability-registry-and-compounding-intelligence.md), [Skill preflight](../skill-runtime-preflight.md) | Map task, applicability, evidence, method, authority, result and qualification to existing records | Capability authors: resolve missing links for a bounded capability; do not introduce a fourth registry |
| Language and context | [Glossary](../wiki/18-Glossary.md), [Memory/Context](../memory-context-architecture.md), [Retrieval](../retrieval-indexing-architecture.md), [Compiled IQ](../compiled-industry-iq.md) | Precise domain terms and selective context loading | Labs assurance: test omissions, stale/conflicting records and scope confusion; compare quality as well as context cost |
| Assurance | [Competency assurance](../wiki/20-Competency-Assurance.md), [domain onboarding](../domain-onboarding-workflow.md) | Separate engineering, product and industrial-validity verdicts; strong matched baselines | Labs reviewers: independent cases, actual treatment receipts and measured results; no uplift from protocol adoption |
| Experience | [Application Contract](../application-contract-v0.2.md), [North Star](../strategy/industry-iq-product-north-star.md) | Consistent evidence, limits, missing inputs and task-resume semantics across applicable surfaces | Studio/Companion owners: authenticated journey proof; Studio remains technical-authority surface and Companion a logical professional experience |
| Release and learning | [Version/status](../version-naming.md), [capability promotion](../capability-registry-and-compounding-intelligence.md) | Separate implementation, CI, deployment, user acceptance and domain qualification; convert verified failures to regression cases | Existing release/promotion owners: preserve rights, independent qualification and approval; no automatic global learning from customer work |

## Capability package crosswalk

Use references to existing records rather than copying their content into a new universal schema. This is an authoring checklist, not a claim that one existing record already enforces every item.

| Question | Existing owner / location |
| --- | --- |
| Who is the capability for and what task does it support? | Persona/competency references and Capability Registry claim |
| Where does the method apply, and where is it excluded? | Versioned domain Skill/method documentation and validated-domain evidence |
| Which evidence, units, freshness and uncertainty are required? | Skill dependencies, invocation-time evidence checks, source/provenance and applicable method contracts |
| What procedure or calculation produces the result? | Protected Industry IQ implementation and typed Functions |
| What may this actor read, recommend or execute? | Host identity, Skill preflight, policy and Action Runtime; READY is not target evidence sufficiency |
| What is returned and retained? | Existing application/Decision contracts; verified Outcome only where an authorized action is reconciled |
| Which claim is supported by which tests? | Capability qualification references and protected independent evaluation records |
| How does the professional inspect or resume work? | Applicable Studio/Companion host contract; a work-item note is not authoritative industrial evidence |

## Sequenced work and acceptance

These are work packages under existing release gates, not new product milestones. Match each to the existing issue tracker before opening duplicate work.

| Package | Dependency | Deliverable and acceptance |
| --- | --- | --- |
| D1 — Reconcile and consolidate guidance | None | This crosswalk and protocol extension are reviewed, linked from existing navigation, checked for broken references, and merged through normal CI. No upstream package installed. |
| D2 — Qualify the comparison design | D1 for shared reporting; existing benchmark gates remain authoritative | Extend the existing Labs comparison: competent generic procedure, matched evidence/tools, actual treatment receipt, independent labels, abstention and failure reporting, latency/cost/effort. Produce a reviewed offline readiness result before any separately authorized billable execution. |
| D3 — Verify the professional journey | D1 for shared reporting; existing host/persistence/security prerequisites govern live acceptance | Extend the existing Studio work-item journey to a reviewable acceptance record: current identity, create/save/resume, stale revision, owner denial, revoked access and explicit missing/unverified evidence. State artifact/configuration and each untested live requirement. |
| D4 — Demonstrate reusable capability coverage | D2 and D3 evidence for the selected capability | Trace one capability through the crosswalk and applicable protocol surfaces; distinguish generic repeatable mechanism from scenario fixtures. Record failures as gaps, not reasons to create new Core abstractions by default. |
| D5 — Evaluate adoption | Comparable completed changes from D1–D4 | Report review/rework rounds, founder interventions, task completion, decision quality, unsafe/over-abstention, latency and cost with sample size and limitations. Keep, revise or remove guidance based on evidence. |

D2 and D3 can be developed independently once the shared reporting convention is available. A docs merge does not complete D2–D5. No deadline, effectiveness improvement or production qualification is inferred from this sequence.

## Boundaries and rollback

- Keep the existing v0.5 CONNECT live-source and verified-writeback critical path. This adoption does not replace it with a documentation milestone.
- Reuse generic host execution; retain industrial evidence, semantics, authority and qualified methods in their existing owners.
- Keep capability-specific details, evaluator answers and measured private findings in Labs. Shared global learning requires independent source-rights and promotion review.
- Add no infrastructure, model provider, spend, deployment, authentication change, mandatory new CI gate or second human reviewer through this guidance.
- If the practices add noise without measurable value, simplify or revert the advisory documents. Existing security, compatibility, release and qualification gates remain in force.
