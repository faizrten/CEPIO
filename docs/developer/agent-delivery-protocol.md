# Agent Delivery Protocol v0.1

**Status:** Engineering guidance for CEPIO contributors and coding agents; **not** a new executable Skill, policy engine, runtime enforcement, or release qualification.

**Scope:** Agent-assisted changes to CEPIO Core. The same principles can inform protected Labs work, but protected scenarios, evaluation labels, proprietary competency logic, and customer evidence must stay in their authorized repositories.

**Intent:** Make AI-assisted engineering more predictable by defining the smallest useful change before editing, verifying the change with independent checks, and reporting uncertainty instead of inflating claims. This adapts the "think before coding, simplicity first, surgical changes, goal-driven execution" themes in the [community coding-skills guide](https://agentpedia.codes/blog/karpathy-claude-code-skills-guide) to CEPIO's existing governance.

## Before changing code

For nontrivial tasks, prepare a **bounded work brief**, preferably in the PR description or task discussion (not a new required form):

1. **Outcome:** What observable behavior or evidence must improve? Identify the relevant release or capability contract; distinguish product release qualification from component progress.
2. **Evidence and uncertainty:** What is verified from code, tests, authorized source material or repository state? Label guesses, missing evidence and disputed assumptions. Do not invent site limits, financial results or operational events.
3. **Reuse first:** Locate existing Core contracts, Industry IQ packages, adapters, tests and CI. Apply **Reuse → Bind → Extend → Own**; do not recreate generic agent or platform infrastructure.
4. **Smallest reversible scope:** State affected files/contracts and explicit non-goals. Prefer one behavior or bounded test per PR; avoid unrelated cleanup, public leakage of protected intelligence or duplicate persistence/integration paths.
5. **Acceptance and counterexamples:** Name focused positive and negative tests, immutable evidence to collect, and what would disprove success. For execution-sensitive paths include authority, tenant isolation, provenance, stale evidence, replay and external reconciliation.
6. **Risk and permissions:** Declare IP class and impact on authorization, secrets, deployment, budgets and customer data. Existing governance remains mandatory; a work brief does not grant approval or spending authority.

A short, routine R0 documentation edit may use a compact description under existing [ADR-0047](../adr/ADR-0047-solo-founder-risk-proportionate-review.md) rules. Do not create unnecessary paperwork for straightforward work.

### Copyable micro-brief (optional)

```text
Desired result / user-visible outcome:
Verified starting evidence (links, commit/ref, test):
Assumptions or unknowns that affect correctness:
Existing capability to reuse:
Smallest intended changes / explicit non-goals:
Security, tenant, source-use, IP, authority and budget impact:
Acceptance checks (positive and negative; exact commands/CI):
Stop conditions / claims that remain unqualified:
```

## During implementation

- Make a **surgical diff**. Preserve interfaces and semantics unless the change is deliberately versioned and migration evidence exists.
- Keep source-specific and customer-specific data in authorized bindings/profiles; keep reusable semantics thin in Core and proprietary Industry IQ/evaluation assets protected.
- Treat a model recommendation, proposed workflow, simulated write or local test as **non-authoritative** unless the appropriate CEPIO runtime and external system have independently qualified it.
- Keep policy/approval checks, secure actor context, source-use rights, tenant isolation, audit, and external write/verify/reconcile behavior in **enforced code**. Natural-language instructions are not security controls.
- When ambiguity is consequential, fail closed or report `UNKNOWN` with the evidence required to resolve it; do not silently assume validity.
- Do not enable paid inference, production deployment, permissions changes or new infrastructure merely to complete an engineering task.

## Verification and reporting

1. Re-read the resulting diff and check for unintended files, weakened gates, public/protected IP crossovers, undocumented new contracts or scope creep.
2. Run the narrowest reproducible positive and adversarial tests, then the existing applicable full CI, compatibility, governance and security checks. Required checks cannot be marked PASS because code looks correct.
3. Record the exact commit/PR, test commands, results, failures, skipped checks and remaining gaps. A test that was not executed is `NOT VERIFIED`, not PASS.
4. If validation fails, revise the smallest relevant change and repeat. Do not fix unrelated components as incidental scope.
5. Keep the canonical maturity score in `config/v1-scorecard.yaml`; a merged PR or passing synthetic acceptance does not independently qualify a product release.

### Industrial judgment analogue — evaluation guidance only

When an Industry IQ Skill evaluates a case such as Rig 07 or K-201, assess these **four reasoning obligations** with protected, independent evaluation cases:

| Obligation | Evidence expected | Failure to catch |
| --- | --- | --- |
| Establish the observation | Source identity, freshness, meaning, missingness, uncertainty and competing interpretations | Fabricated sensor value, stale observation presented as current, unsupported causal claim |
| Prefer the smallest warranted explanation | Conditional hypotheses ranked by available discriminating evidence, explicit alternatives and evidence gaps | Premature diagnosis, invented site-specific threshold |
| Recommend a bounded next step | Least-risk justified intervention, accountable role, applicable approval, and separation of recommendation from execution | AI self-approval, unauthorized machine control or unsupported economic benefit |
| Verify before calling it an outcome | Read-back, independent reconciliation, trusted provenance and appropriately authorized outcome record where a real action occurred | Treating draft, simulation or accepted API request as verified external change |

This is **not** a new four-stage agent runtime, a replacement for the CEPIO Skill Registry, or permission to promote synthetic conclusions into field truth. It is a checklist for existing Industry IQ evaluation and assurance contracts. Only the existing host-bound CEPIO policy, Action Runtime and source authorities can govern real-world side effects.

### Measuring whether adoption helps

For a bounded sample of comparable future work, compare the previous approach with this guidance using: unintended files per PR; first-pass focused-test success; adversarial failures caught before merge; rework rounds; elapsed review/merge effort; and real evidence of supported vs unsupported claims. Keep the evaluation protocol, expert labels and answer keys in CEPIO Labs where protected. Do **not** claim an improvement or increase the v1 score without independent evidence.

For industrial reasoning, measure evidence-grounding, appropriate abstention, conditional hypothesis quality, intervention/authority compliance and verified-outcome integrity **separately** from writing style. An LLM given better instructions is a useful evaluation arm, but does not replace CEPIO's enforceable semantic and governance contracts.

## Rollout and rollback

- Begin with advisory instruction in `AGENTS.md`, documentation and existing CI; no new PR-required workflow, second human approval, model provider or billing mechanism.
- Review after comparable tasks produce measurable evidence. If the guidance creates noise or encourages unnecessary process, simplify or remove the instruction and its documentation through a normal PR.
- All existing branch protections, security/CodeQL gates, scorecard governance and public/protected/customer boundaries remain unchanged.
