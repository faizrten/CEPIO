# IC-2 — Host-scoped industrial competence routing (source-only candidate)

**Status:** additive, internal-only candidate extension **stacked on Core IC-1 PR #364**; not merged, deployed or field-qualified. **Tracking:** Core #365. **Classification:** public source-neutral reference interface, no protected Labs prompts, labels, scoring logic or customer content.

## Reason for the increment

The first protected, synthetic six-case DEVELOPMENT ablation showed that an otherwise safely refused task could return `NO_MATCH` before its missing/conflicting evidence was explained. The detailed cases and independent-evaluation methods remain in protected Labs. This extension tests a **host-scoped alternative** without relaxing the original lexical threshold or accepting untrusted capability hints.

The additive internal entry point is `activate_competence_with_host_context`. The original `activate_competence` function and signature remain unchanged for existing callers. No new REST/MCP route is published.

The behavior is deliberately narrow: when an approved application supplies *authenticated, authorized and source-resolved* **asset/domain/type/workflow** context, the existing Capability Router still attempts normal lexical routing. If no lexical route passes the original threshold, CEPIO may screen eligible methods using **at least two non-generic task terms** that overlap with the method's declared title and description. The method must also match all three host-scoped selectors through existing registry metadata:

- `validated_domains`: exact domain identifier;
- `semantic_terms`: exact asset-type term tail;
- `competencies`: exact workflow kind.

No match returns `NO_MATCH`; equal leading matches return `AMBIGUOUS`. The authorized, source-admitted evidence gates execute **after** selection and can return `BLOCKED` with precise prerequisites. Candidate routing never means a Skill is READY or an industrial diagnosis, operational approval or verified outcome has occurred.

## Internal contract

`ActivationScope.permitted_context_refs` is a distinct host-issued set of actor-visible, source-authorized context identifiers. The optional `ActivationHostContext` contains:

- exact authenticated `actor_id` and `tenant_id`;
- resolved `asset_id` and exact registry `domain`, `asset_kind`, `workflow_kind`;
- source-owned `source_ref` and timezone-aware `observed_at` / `valid_until`.

Before routing, the gate requires the context actor/tenant/asset to equal the host's `ActivationScope` and `ActivationTask`, the source reference to be present in `permitted_context_refs`, and the task timestamp to fall in the context's validity window. Invalid or expired context returns `HOST_CONTEXT_NOT_ADMITTED` **without** exposing capability IDs or evidence references. An unauthorized asset remains `ASSET_NOT_AUTHORIZED` and is denied before any context check.

**Trust invariant:** neither this Pydantic record nor its `source_ref` can authenticate the host or attest an industrial source by itself. This function is not exposed as a raw REST/MCP tool. The serving host must independently verify the user/agent identity, actual source access, asset crosswalk, workflow membership, freshness and canonical value before creating both `ActivationScope` and `ActivationHostContext`. A model or browser must not choose those fields, construct the allowlists or request a context source by naming an ID in a prompt.

A capability's `QUALIFIED` or `PRODUCTION` metadata label remains **necessary but insufficient** to claim applicable field competence. Registry evidence references and fixture timestamps are not independent field assurance.

## Routing behavior

| Situation | Result |
| --- | --- |
| No `host_context` | Original IC-1 lexical router, untouched behavior |
| Context present but identity/source/time not admitted | `BLOCKED / HOST_CONTEXT_NOT_ADMITTED` |
| Context admitted but no matching domain + asset type + workflow | `NO_MATCH / NO_CONTEXT_MATCHED_CAPABILITY` |
| Lexical route passes original threshold within matched context | Original ranking and ambiguity rules; `routing_basis=LEXICAL` |
| Lexical route below threshold, task has 2+ meaningful overlapping method terms | Unique candidate only; `routing_basis=HOST_SCOPED_CONTEXT`, `route_score=null` |
| Two equally supported fallback candidates | `AMBIGUOUS / MULTIPLE_CONTEXTUAL_CAPABILITIES` |
| A matched method lacks admitted instance evidence | `BLOCKED` with the existing missing/conflict/staleness reason codes |
| Context matched but task is unrelated or underspecified | `NO_MATCH` |

The fallback's two-term screen is a **development heuristic**, not calibrated statistical confidence, not a semantic decision classifier and not an unconditional route based on asset metadata. Asset identifiers and common generic words are excluded from the fallback lexical comparison. It cannot guarantee high precision for all prompts and must be tested against unseen distractors and adversarial task requests before any broader activation.

## Verification and scope

Additive synthetic tests check: successful candidate and explicit missing/conflicting evidence blocks; unchanged no-context route threshold; expired/future and wrong-actor, wrong-tenant, wrong-asset or unpermitted source; wrong domain/asset type/workflow; not-qualified and not-permitted capabilities; ambiguity; unrelated requests and attempts to override tenant/capability by prompt. Both `route_score` and `routing_basis` distinguish heuristic fallback from ordinary lexical routing.

Run `pytest -q tests/test_competence_activation_host_context_ic2.py tests/test_competence_activation_ic1.py tests/test_retrieval_routing_indexing.py`, then full Core and quality CI. No external network, new dependency, paid inference, identity change, database migration, hosting integration, operational Action or production deployment is included.

## How to assess real improvement

Retain the earlier protected 3/6 visible synthetic run **unchanged**. Compare against this new contextual path using the exact same frozen six development cases, no changed prompts or source facts. Report original and new outcomes, the added host-context evidence and errors separately; any improvement is **in-sample software routing** only. Create a new independent, sealed and domain-reviewed corpus to evaluate precision, false positives, safe refusal, source admissibility and industrial decision quality. Do not present a development regression pass as model uplift.

The remaining proofs are exact host identity/source attestation, independently qualified applicability and methods, trusted invocation receipts, matched LLM comparison, professional review and an explicit production release gate. This PR does not close Core #365 or Labs #235 by itself.
