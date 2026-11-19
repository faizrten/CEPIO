# IC-2 P0 — Request-bound industrial task-admission contract

**Source-only security candidate** stacked on Core PR #366, tracked by Core #367. Does not authorize deployment, Microsoft Copilot activation, backend configuration, external actions or inference. Original IC-1 and host-context functions and signatures remain unchanged.

## Why this boundary exists

The first six visible synthetic development tasks improved from **3/6 to 6/6** with host asset/domain/type/workflow context. A separately preregistered **20-task adversarial DEVELOPMENT** challenge then recorded **14/20** software expectations with **six incorrect competence candidates** for unrelated, explicitly negated or wrong-asset requests. Neither set is independently sealed, expert-reviewed or evidence of industrial judgment uplift.

**Conclusion:** an authorized industrial asset in view does not establish the *current user's requested job*. Asset-scoped keyword overlap must not be treated as an implicit instruction to investigate.

This increment adds a narrow **deliberately initiated investigation path**, not a universal automatic intent classifier. In particular, the source-only model does **not** solve implicit host activation for arbitrary Copilot conversations. That remains blocked until a separately evaluated and host-controlled task admission capability exists.

## New host-only entry point

`activate_competence_with_task_admission` is defined in `src/cepio/task_intent_admission.py`. It wraps, rather than replaces, `activate_competence_with_host_context`.

An authorized host injects a **private** `AuthorizedTaskEventResolver`. Instead of accepting a caller's `trusted: true`, JSON event body, capability hint, target selector or LLM decision, the function asks that resolver for an event bound to:

- exact authenticated actor, tenant, session and request ID;
- exact current user-request UTF-8 SHA-256 digest;
- the same independently authorized asset and host context source reference;
- an aware, positive timestamp window no longer than **10 minutes**, with the task instant inside it;
- the user's requested target asset(s), resolved by the host from an explicit investigation workflow/control;
- a host-verified event origin proving the user **explicitly initiated** the engineering investigation, not just that a page displayed engineering data or an LLM suggested investigation.

An unresolved, unavailable, stale, cross-tenant, cross-session, cross-request, altered-prompt or model-inferred event returns `BLOCKED / TASK_INTENT_NOT_VERIFIED` **without a capability ID or evidence references**. Explicit general, cancelled or declined work returns `NO_MATCH / TASK_NOT_AN_INVESTIGATION`. A request targeting a different or multiple assets returns `BLOCKED / ASSET_INTENT_CONFLICT`. An unauthorized scope asset fails before the event-store read.

Only after these checks may the existing **optional host-scoped** routing and evidence admission run. That delegated path still distinguishes `CANDIDATE`, `BLOCKED`, `AMBIGUOUS`, `NO_MATCH` and the underlying missing, conflicting or stale engineering evidence. A `CANDIDATE` is never a method qualification, finding, Decision, operational recommendation, approval, Action or Outcome.

## Authentication and trust caveats

**The event model is not an attestation or signature.** Source-only Python cannot prove the event store belongs to a trusted host or that a human really clicked an investigation control. A real implementation must inject the resolver from an independently verified CEPIO/Entra session, with server-owned event generation, session-bound lookup and source/asset crosswalk authorization. Never expose the resolver or raw event model as MCP tool arguments, an HTTP request body, or a browser query parameter.

The user-request digest protects equality of a current turn to its recorded event; it is **not** a proof of user intent. A prompt can still name a different asset or explicitly negate work while an incorrectly implemented host issues a positive event. In that case, this source-only wrapper **cannot independently determine the discrepancy**. The host must refuse to issue a positive event until the requested task and actual target are independently verified. A future implicit Copilot path requires independently calibrated task-intent and requested-target admission, not a hardcoded phrase blacklist or model-supplied `intent` field.

For now, *safe user-initiated investigations can become low-friction; passive implicit activation in arbitrary conversations stays blocked.* This is an intentional product trade-off, not completion of the North Star.

**Privacy:** Retain only minimum-lived session event references and digests in a verified host; do not create a global prompt cache, cross-tenant intent store or long-lived conversational telemetry for this gate. No logging of user prompt text is introduced by this module.

## Tests and no-spend controls

`tests/test_task_intent_admission_ic2.py` covers a fictional reliability asset, fake same-session event resolver, case-appropriate investigation, general/e-mail and declined work, passive/model-inferred origin, wrong or multiple targets, cross-actor/tenant/session/request replay, altered digest, source mismatch/expiry, event-store failure, unauthorized asset, conflicting/missing evidence, and invalid caller-supplied authority flags.

Run:

```bash
pytest -q tests/test_task_intent_admission_ic2.py tests/test_competence_activation_host_context_ic2.py tests/test_competence_activation_ic1.py
```

Then all Core CI, static, compatibility, security and coverage checks. These tests use fictional maturity and source-admission labels to exercise a contract; **no independent source attestation, model trial, industrial expert sign-off or real host invocation is established by passing**.

## Microsoft host path — still separate

An eventual Microsoft 365 Copilot Studio or Teams experience must reuse the canonical authenticated CEPIO `/mcp` endpoint and its existing read-only client restriction; **this PR does not introduce a new endpoint or tool**. The host must validate real Entra issuer/audience/tenant/delegated principal/client ID and actor-scoped industrial source rights. It must then create and resolve an authenticated, request-bound task event based on the user's *actual* task, not merely system-wide Work IQ/asset context.

Do not turn on automatic tool selection or publish the managed-agent integration based on synthetic source checks. Continue the independent expert-reviewed task-precision and matched model-quality work in protected CEPIO Labs #235, with Core #367 as the admission owner. Published scorecards and production qualification remain unchanged.
