# Trusted Companion Across the Work Cycle — Development Plan

Date: 2026-11-05 (Asia/Riyadh)
Status: PROPOSED delivery backlog; not an implementation, qualification or release claim.

## Product agreement

CEPIO helps customer professionals solve their own problems throughout their work. Rig 07 is a synthetic evaluation case, not a feature, product workflow or customer-facing identity. Expert review supports the whole process; it does not define the product.

Use four stages: understand the desired result and task; understand risks and requirements; execute and manage change; learn and improve. Common understanding spans all four. The user-supplied pre-/after-work dialogue card inspired this process mapping; this document does not claim Equinor endorsement or implementation of an official standard.

Companion applies the process to professional work. Studio applies it to developing, inspecting, qualifying and improving the capabilities that support that work. Users may enter at any stage, skip irrelevant questions with a reason, and revisit earlier answers when conditions change. Do not build a mandatory questionnaire or a second agent runtime.

## Evidence and limits of this assessment

Targeted default-branch inspection, not an exhaustive code audit or deployment verification. Search results observed Core commit d01d3197ddb45bead343fe30343d3df2b2bc67ff and Studio ab1e2c2c556faa587a189bd57868f34a124c5e1d. Full reads and search excerpts are distinguished below. A missing search result is not proof of missing functionality. No tests, live systems or inference were run for this planning assessment. No protected Labs methods or evaluation contents are reproduced.

| Foundation | Evidence inspected | Reuse decision / remaining gap |
| --- | --- | --- |
| Product direction | Full read: industry-iq-product-north-star.md | Already supports professional work, sovereign learning and cross-industry aspiration. Extend delivery mapping, not the mission. |
| Operating primitives | Full read: ../../AGENTS.md | Documented foundation includes identity, temporal evidence, Decisions, Actions, workflows, outcomes, registries and memory. Verify individual interfaces in implementation tickets. |
| Evidence and uncertainty | Full read: ../adr/ADR-008-core-evidence-uncertainty.md | Reuse evidence, assumptions, dependencies and supersession semantics. End-to-end answer dependency invalidation still needs qualification. |
| Work items | Full read: ../../src/cepio/drilling_npt_iq.py | Concrete domain investigation creates a WorkItem with actor/reason and relationships. Not a general professional work-cycle contract. |
| Management projection | Full read: ../../src/cepio/management_contract.py | Tenant-scoped investigation aggregates require a trusted observer. This is not persistent customer work context or a mutation API. |
| Outcomes | Search excerpt: ../../src/cepio/kinetic_external.py | Frozen WorkflowOutcome model exists. Verify linkage to user expectations, debriefs and source outcomes before extending. |
| Context | Search excerpts: ../../src/cepio/memory.py and ../wiki/22-Memory-and-Context.md | Bounded ContextAssembler exists; ephemeral working context is not durable work continuity. |
| Objectives/accountability | Search excerpts: ../../src/cepio/performance_contract.py | PerformanceContract exists; inspect objective and responsibility reuse before proposing new types. |
| Studio | Full reads in this session: Studio README, src/lib/labs/rig07.ts, docs/learning-studio-and-technical-review-roadmap.md | Existing protected integration and proposed technical-review experience are foundations. General four-stage customer-neutral UX is not established by these reads. |

Classification: reusable foundation / extension candidate / not established. No component is declared qualified by this inventory.

## Complete question-to-capability map

All rows require source references, applicability, uncertainty and explicit unresolved status. F = foundation identified above; E = extension candidate; U = implementation/qualification not established.

| ID / professional question | Required behavior and inputs | Reuse / gap | Acceptance evidence |
| --- | --- | --- | --- |
| Q01 What is the job and tasks? | Clarify objective, scope, task dependencies and success criteria using user intent and authorized asset/process context | F work items/performance; E task synthesis | Ambiguous intent prompts clarification; customer supplies arbitrary problem without fixture IDs |
| Q02 Who is responsible for what? | Propose role/task assignments from authorized responsibility records; people confirm ownership | F identity/accountability; U assignment confirmation | Unassigned/conflicting ownership remains visible; model cannot impersonate confirmation |
| Q03 Which requirements apply and how? | Retrieve applicable versioned procedures; explain task-specific steps and conflicts | F retrieval/evidence documented; U applicability assurance | Stale, incompatible or unavailable requirement cannot appear authoritative |
| Q04 What workplace risks exist? | Relate task to local condition, concurrent activity and hazards; request missing observations | F domain semantics; U situational completeness | Unknown site conditions remain unknown; hazards cannot be declared absent from missing data |
| Q05 What can go wrong and when do we stop? | Explore failure modes and consequences; link stop/escalation conditions to approved sources and human authority | F uncertainty/policy; E stop-condition composition | Scenario change triggers relevant escalation; generated threshold cannot become approved limit |
| Q06 Do we have what we need? | Check competence, evidence, tools, materials, permits and isolations against task prerequisites | F preflight documented; E work readiness | Missing or contradictory prerequisite blocks a readiness assertion |
| Q07 Who must collaborate? | Identify expertise and affected teams from authorized context; prepare focused handoff | F roles/capabilities; U collaboration mapping | No invented contact/credential; no automatic message or invitation |
| Q08 Does everyone understand tasks and risks? | Role-specific briefs and human teach-back; surface disagreements | U shared-understanding interaction | AI never marks human understanding confirmed; conflicting interpretations persist |
| Q09 How did the job go? | Compare expected versus observed outcome with source evidence | F WorkflowOutcome; E debrief | Distinguish user-reported, simulated and source-verified outcomes |
| Q10 What went well and why? | Explain supported contributing factors; preserve causal uncertainty | F evidence/uncertainty; E outcome reasoning | Correlation alone does not establish causation |
| Q11 What surprised us? | Compare actual events with prior assumptions and predictions | F temporal/evidence; E expectation comparison | Previously unknown information remains distinguishable from information available at decision time |
| Q12 What changed and how did it work out? | Record reason, affected decisions, reassessment and observed result | F history/workflow; E change impact | Prior answer is retained and visibly superseded; old approval cannot silently cover changed scope |
| Q13 What should differ next time? | Propose scoped improvement with evidence and evaluation need | F capability governance documented; E lesson proposal | Single success cannot automatically promote a general method |
| Q14 How do we share learning? | Produce audience-appropriate, rights-aware lessons for approved sharing | F sovereignty doctrine; U sharing workflow | Tenant-private evidence cannot leak into global learning or another customer |

Execution bridge: use suitable Skills, calculations and specialist methods to resolve the user's substantive problem. These questions organize assistance; they are not substitutes for engineering competence. Revisit affected Q01–Q08 when new evidence changes applicability, risk, readiness or responsibilities.

## Shared work context: composition proposal

Start with a domain-neutral application projection referencing existing contracts, not a new canonical Core object or database. The implementation spike must justify any genuinely missing reusable primitive.

Proposed fields/references:
- work identity, schema/revision, trusted tenant and actor scope;
- objective, success criteria, task/subject references and selected stage;
- requirement versions and applicability rationale;
- evidence references, validity/freshness, source-use rights and known gaps;
- claims, assumptions, dependencies and uncertainty;
- responsibility proposals, confirmed human assignments and collaboration needs;
- recommendations, Decisions, approval/Action references and authority limits;
- change events, affected assessments and supersession links;
- expected/observed outcomes and reviewed lesson candidates.

A question answer is supported, provisional, unresolved, escalated or not applicable with a reason. Do not confuse these answer states with execution permission or capability qualification.

Durable records preserve provenance; bounded ContextAssembler selects only authorized relevant context for a turn. Recheck rights on resume. Existing source systems remain authoritative. Concurrent edits require revision guards. Retention/deletion and source-rights revocation must be designed before customer persistence.

## Paired experience

| Stage | Companion | Studio |
| --- | --- | --- |
| Understand | My objective, situation, tasks, success and ownership | Target professional question, scope, examples and acceptance criteria |
| Assess | Applicable requirements, risks, unknowns and prerequisites | Required sources, methods, competence, failure modes and authority ceiling |
| Work and adapt | Investigate, compare, recommend, track decisions and reassess changes | Compose capability, run trials, inspect failures and compare revisions |
| Learn | Outcome, surprises, supported lessons and handover | Evaluation conclusions, improvement candidate, regression and promotion status |

Persistent context panel: objective; supported findings; open questions; responsibilities; changes; outcome. Evidence is expandable. Synthetic data is labelled. Progress is not a green safety/compliance score.

Studio uses the same reasoning discipline without giving builders operational authority. Retain existing navigation during the first isolated preview; test the four-stage workbench before navigation replacement.

## Ordered engineering backlog

All tickets below are proposed and not started unless explicitly noted. Owners are component responsibilities, not named-person assignments. Effort bands are planning estimates, not dates: S = a few focused engineering days; M = approximately one engineering week; L = split after spike.

| ID | Deliverable / responsible component | Dependency | Exit gate | Estimate |
| --- | --- | --- | --- | --- |
| WC-00 | Capability map and targeted evidence inventory / Product | None | All 14 questions and execution bridge mapped; source/claim limits explicit | This draft |
| WC-01 | Interface reuse spike / Core + application layer | WC-00 | Inspect PerformanceContract, WorkItem, memory, Decision, WorkflowOutcome, registry/preflight and ACCC interfaces/tests; field-level reuse matrix; no unnecessary Core concept | S |
| WC-02 | Work-context projection and persistence design / application layer | WC-01 | Versioned schema, adapter plan, tenant/rights enforcement, concurrency and resume semantics; compatibility decision | M |
| WC-03 | Question-to-capability routing / Industry IQ | WC-01 | Map intent to admitted capabilities and evidence needs; resolve/clarify/abstain paths; no fixture-specific branches | M |
| WC-04 | Paired four-stage isolated preview / Studio + Companion surface | WC-02, WC-03 design | Arbitrary user problem entry; relevant questions only; sources/gaps; resume and changed-evidence walkthrough | M |
| WC-05 | Change impact and reassessment / application + Industry IQ | WC-02, WC-03 | Identify affected assumptions/recommendations; preserve history; invalidate stale review scope; unknown dependencies escalate | M |
| WC-06 | Shared understanding and expert collaboration / experience layer | WC-04, WC-05 | Confirmed human ownership/teach-back distinct from AI text; version-bound challenges; no unrequested messaging | M |
| WC-07 | Outcome/debrief and scoped lesson candidates / Industry IQ + Labs | WC-02, WC-05 | Expected vs actual, evidence class, attribution limits and tenant-private lesson handling | M |
| WC-08 | Independent multi-case qualification / Labs | Criteria begin at WC-00; execution after WC-03–07 | Held-out cases, matched-model/tools baseline, negative cases and failure receipts; no answer-key exposure | M |
| WC-09 | Customer-owned problem pilot / product + existing integrations | WC-08 plus applicable integration/security gates | Authorized real context; repeated usefulness; supported conclusions and explicit gaps; user feedback | L |
| WC-10 | Governed improvement and domain expansion / Labs + Industry IQ | WC-07–09 | Rights-cleared candidate, independent regression, scoped qualification and governed promotion | L |

Next implementation slice is WC-01, then WC-02/03 and WC-04. Do not start by making Rig 07 a generalized customer workflow.

## Qualification and release alignment

Use at least three materially different evaluation contexts: Rig 07 as one synthetic case, a distinct process-equipment problem, and another task family such as work preparation. Include missing, stale and contradictory evidence; an unqualified domain; changed conditions; revoked rights; unauthorized actions; and unknown outcomes. Choose exact private fixtures in Labs. A customer-shaped test accepts user-supplied problem/evidence without scenario lookup.

Report process coverage (questions supported), implemented capability coverage, independently qualified task/domain coverage and customer outcome evidence separately. A universal percentage obscures these differences.

Measure task success, material unsupported conclusions, useful abstention, consequential omissions, time/effort, change-response correctness and traceability against a matched baseline. Predefine rubrics and thresholds before evaluating; do not infer trust from engagement or scenario counts.

Release dependencies remain:
- v0.5 CONNECT: authoritative customer context and governed integration proof remain critical.
- v0.6 EXECUTE: verified outcomes and complete supported work are relevant.
- v0.7 EXTEND: independent builders reuse the Studio process.
- v0.8 OPERATE onward: dependability and generalization still require their own evidence.

This proposal does not alter release gates, canonical score, production posture, permissions, inference spend, deployments or Rig 07 mutation settings. It adds no new service or generic runtime.

## Decisions and next evidence

Agreed product direction: complete work-cycle companion, mirrored discipline in Studio, synthetic cases as proof only.
Proposed implementation choice: application-level composition before new Core primitives.
Open technical questions for WC-01: durable context repository fit, exact identity/rights propagation, change dependency coverage, current ACCC adapter interfaces and existing test coverage.
Open pilot questions for WC-09: customer, authorized sources, bounded professional task, acceptance rubric and operational owner.

Validation for this document: all 14 card questions mapped; four stages represented on both surfaces; backlog dependencies and acceptance gates stated; public sources only; no new implementation or qualification claims.

## WC-01 execution update — 2026-11-05

[Contract reuse spike](work-cycle-contract-reuse-spike.md) records inspected interfaces, a local memory probe and concrete integration boundaries. Bounded interface assessment completed; full pytest execution was unavailable, and persistence adapter qualification remains open. Next deliverable: WC-02 read-only work-context projection and synthetic contract checks. No runtime or release status is changed.
