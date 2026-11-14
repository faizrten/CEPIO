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

## Manufacturing workflow alignment — issue #361 / PR #362

The manufacturing review refines D1–D5 below; it creates no parallel roadmap, runtime, registry or release gate. The bounded candidate is a recurring-equipment investigation with a reviewable next evidence request and retained decision history. Rig 07 and K-201 remain evaluation fixtures, not product features. Scope implementation through the existing owners and record absent behavior as a gap.

| Lesson / user outcome | Existing owner and package | Acceptance evidence to collect |
| --- | --- | --- |
| Reach useful work from available exports | Bindings, onboarding and application experience; D3/D4 | A rights-scoped file intake preserves source identity, time, units and freshness. Show task-level available/limited/blocked status without conflating it with Skill READY. Exports provide an entry path; they do not satisfy CONNECT live-source or writeback gates. |
| Make safe partial progress | Skill evidence/applicability checks and Decision contracts; D2–D4 | Missing evidence blocks only the conclusions/actions that require it. A limited result identifies justified observations, unresolved questions and a feasible next check; mandatory evidence and authority checks remain fail-closed. |
| Maintain dependable operational context | Existing identity, temporal, provenance and context owners; D2/D4 | Test ambiguous assets, source conflicts, clock misalignment and changed configurations. Auto-ontology proposals remain unverified until the applicable confirmation process establishes their status; a graph relationship is not proof. |
| Explain what changed | Decision/evidence history and host experience; D3/D4 | Change an evidence version, identify dependent conclusions and required rechecks, preserve the historical result, and visibly qualify any stale recommendation. Re-evaluate affected authorization/approval under existing contracts; never silently reuse approval for a materially changed action. |
| Preserve qualified experience | Existing memory, Outcome and promotion contracts; D2/D4 | Distinguish proposed explanation, investigation evidence, completed action, verified effectiveness and superseded conclusion using existing records. These are review distinctions, not a new canonical state enum. Tenant experience does not automatically become global Industry IQ. |
| Propose the next useful evidence | Industry IQ methods and existing information-gain semantics; D2/D4 | Evaluate whether the suggested check distinguishes hypotheses and is feasible, proportionate in cost/time and safe within the actor's authority. Keep hypothetical estimates labelled; seeking evidence is not permission to intervene. |
| Make review easier | Application Contract and Studio/Companion owners; D3 | The intended actor can inspect changes, source/calculation basis, contradictions, missing evidence and the specific decision needing attention; then save/resume. Assess visualization by review usefulness. Do not require every field on every host or create a second login/runtime. |
| Qualify reusable capabilities | Existing Skill/Capability/Pack and qualification owners; D4 | Identify accountable owner, method/version, supported scope, prerequisites, failure cases, evaluation references and retirement/replacement path. Distinguish written instructions from enforcement actually exercised through the caller interface. |
| Prove value against a realistic alternative | Existing protected Labs comparison; D2 | Compare a competent frontier-model procedure with matched generic tools/evidence against the same setup plus actual CEPIO treatment. Include a deterministic arm only where executable. Test evidence-change handling and next-check quality as well as judgment, unsafe/over-abstention, review burden, latency and cost. |
| Demonstrate recurring usefulness | Existing adoption work; D5 | Record time to first useful result, founder assistance, voluntary second-case use or return to an investigation, and reuse of verified findings, with consent, sample size and limitations. A guided demonstration is not retention or industrial qualification. |

Before widening implementation, classify relevant backlog items as reuse/adapt, build for a demonstrated gap, or defer/stop. Prioritize first value, decision quality and dependable follow-through while preserving v0.5 CONNECT. Additional skill catalogs, frameworks or visualization breadth need a concrete contribution to those outcomes.

### Source and adoption boundary

Design references reviewed on 14 November 2026: [Claude for Manufacturing README](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/claude-for-manufacturing/README.md), [launch article](https://claude.com/resources/articles/claude-for-manufacturing), and [root-cause skill](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/claude-for-manufacturing/skills/root-cause-capa/SKILL.md). These are mutable references, not a pinned implementation audit or executed benchmark. The README describes an unmaintained reference implementation; the article's product direction does not establish support for that checkout. This alignment independently describes design lessons and imports no source, connector or dependency. Any later reuse must pin the exact revision and satisfy the existing OSS Dependency Resilience Gate, including applicable licensing, security, maintainability and fallback review.

All rows are acceptance targets or review guidance, not implementation claims. D1 documentation can close only through its existing checks and merge evidence; D2–D5 remain separate proof.

## Cross-company handoff acceptance — bounded D2–D5 extension

Use one operator-to-service-provider handoff within the selected investigation to examine whether existing Decision, Action, Binding, provenance and Outcome contracts can represent the exchange. This is acceptance guidance, not a new intercompany ERP, commercial-commitment schema or permission to contact a counterparty.

Keep engineering justification, the operator's internal authorization, and the provider's acceptance distinct. Submission or transport acknowledgement does not prove acceptance of the request or its terms. A verified local Outcome does not establish counterparty acceptance, receipt of service or verified repair effectiveness.

| Package / existing owner | Bounded acceptance target | Failure or counterexample |
| --- | --- | --- |
| D2 — Protected assurance | Evaluate recommendation, internal approval, submission, counterparty acceptance, service completion and effectiveness as distinct evidence-backed claims; use the matched baseline and independent reference cases already required. | A successful API response, an agent's assertion, silence or a local approval is promoted to counterparty commitment or completed work. |
| D3 — Application / Studio journey | Show the pending party, requested next step, accepted request version and conditions where evidenced, conflicting confirmations, and source/freshness. Preserve save/resume and authorized visibility. | A waiting, rejected, expired or disputed exchange appears complete; another party's restricted evidence is exposed to explain a status. |
| D4 — Existing runtime and binding owners | Trace one exchange from authorized proposal through authenticated counterparty response, changed terms, rejection and reconciliation. Reference each party's own authority, request/version correlation and permitted evidence; identify gaps before proposing contract changes. | A response from the wrong party or for an older request is accepted; one organization's credentials or approval confer authority in another. |
| D5 — Adoption evidence | Report handoff completion criteria, time waiting for each party, manual reconciliation effort and unresolved/rejected/disputed handoffs, with sample size and limitations. | A sent message or accepted transport request is counted as completed coordination; synthetic timing is claimed as field value. |

For the D4 proof, record positive and negative observations through the actual supported interface:
- A response from the authorized provider confirms the identified request version and conditions; subsequent work and effectiveness still require their own evidence.
- Missing, rejected or conflicting acceptance remains explicit; timeout is not consent.
- Changed scope, timing or terms invalidate any inferred applicability of prior acceptance. Preserve the original history and obtain the applicable new authorization/acceptance before execution.
- Duplicate delivery and retry do not create duplicate commitments or side effects; out-of-order or stale responses cannot silently overwrite newer state.
- Revoked access and cross-tenant reads fail under each organization's policy. Exchange only authorized evidence; shared visibility does not imply shared authority.
- External failures, cancellation requests and disputed completion remain distinguishable from confirmed cancellation or reconciled completion. Do not claim a distributed rollback when only a local step was reversed.

Use existing identifiers and records where they suffice. If acceptance semantics are missing, record the smallest concrete gap and route any implementation through the existing contract/version review. These distinctions do not introduce canonical enums or assert commercial/legal enforceability. Start with synthetic or offline proof; live exchanges, commercial commitments and customer data require their applicable existing authorization. Keep v0.5 CONNECT live-source/writeback requirements intact.

## Boundaries and rollback

- Keep the existing v0.5 CONNECT live-source and verified-writeback critical path. This adoption does not replace it with a documentation milestone.
- Reuse generic host execution; retain industrial evidence, semantics, authority and qualified methods in their existing owners.
- Keep capability-specific details, evaluator answers and measured private findings in Labs. Shared global learning requires independent source-rights and promotion review.
- Add no infrastructure, model provider, spend, deployment, authentication change, mandatory new CI gate or second human reviewer through this guidance.
- If the practices add noise without measurable value, simplify or revert the advisory documents. Existing security, compatibility, release and qualification gates remain in force.
