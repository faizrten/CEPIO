# IC-1 — Implicit Industrial Competence Activation v0.1

**State:** Host-only, source-only candidate routing prototype. **Not** a production deployment, hosted tool, field-qualified engineering method, diagnosis engine, permission to act, new Industry IQ package, or published release guarantee.

**Strategic goal:** Make relevant industrial competence discoverable without requiring a professional to select a Skill, while keeping evidence, uncertainty and authority explicit. This extends the [Industry IQ North Star](strategy/industry-iq-product-north-star.md) under **Reuse → Bind → Extend → Own**.

## Observable behavior

Given a natural-language industrial task, a host-resolved asset identity and authenticated actor/tenant scope, `activate_competence`:

1. Checks that the host has permitted the asset before any routing;
2. Filters the existing Capability Registry by host-permitted IDs and `QUALIFIED` / `PRODUCTION` maturity *labels*;
3. Uses the existing deterministic `CapabilityRouter` with a bounded `RetrievalIntent`, not an additional agent, graph or index;
4. Abstains when no route passes the lexical screening threshold or two candidates are too close;
5. For the selected capability, requires declared evidence types, some recorded registry qualification reference, and host-admitted evidence for the **same tenant and asset** with matching exact evidence type and valid time;
6. Fails closed on missing, conflicting, unverified, stale or future-dated required evidence;
7. Returns a `CANDIDATE` for **further authorized review**, or `BLOCKED`, `NO_MATCH`, `AMBIGUOUS` with reason codes. It returns **no root-cause inference, Decision, approval or Action**.

Source IDs enter the output only when the task passes the candidate gate. Denied/unpermitted/foreign evidence does not appear in result references. Capability IDs are never disclosed for denied assets or a scope with no permitted capabilities.

### Status meanings

| Status | Meaning | Allowed next step |
| --- | --- | --- |
| `CANDIDATE` | A route exists and declared host-evidence prerequisites were met | Authorized host may request independent qualification / Skill preflight and invocation-time evidence validation |
| `BLOCKED` | Missing or conflicting required prerequisites or unauthorized asset | Request the right source/identity; do not diagnose or execute |
| `AMBIGUOUS` | Multiple similarly matched methods | Resolve task/engineering applicability with the professional |
| `NO_MATCH` | No sufficiently matched *permitted and maturity-labelled* method | Ordinary assistance or safe refusal, without a CEPIO competence claim |

`CANDIDATE` **does not mean** `READY` Skill dispatch, real-time data sufficiency, calibrated confidence, independently verified Capability Passport, engineering method validity or safety sign-off. A Registry maturity label and an evidence reference are **insufficient** to prove the latter.

## Trust and provenance boundaries

- `ActivationScope` is **host-issued** after authentication and CEPIO policy checks. It must not be populated from a browser, LLM argument, tenant name in prompt, arbitrary model claim, or the `asset_id` alone. Its permitted asset, capability and evidence-ref sets are host-curated for this actor and request.
- `ActivationTask.asset_id` and `at` must be resolved and time-bound by the authorized host. A similar equipment tag from a prompt is not sufficient identity.
- `EvidenceAdmission` is **host-issued** after external source authorization and provenance/time/identity checks. The `HOST_ADMITTED` field is a local admission label, **not a cryptographic source attestation**. A client passing `HOST_ADMITTED` in JSON does not make its evidence trustworthy; **do not expose this entry point as a raw public payload endpoint**.
- `ActivationPolicy.minimum_route_score` and `ambiguity_margin` are *lexical screening heuristics*, not statistical probabilities of task or method correctness. Route reasons and score are not confidence or a risk estimate. Any production routing thresholds require independent calibration on held-out tasks.
- Capability `PROFILE` materials and all evidence remain subject to source/tenant policy. This reference implementation uses no cross-tenant index, embeddings, learned profile, prompt capture or memory writes.
- Competing receipts for the same source with inconsistent status or timing, or any explicitly conflicting/unverified evidence for a required type, block the candidate; selecting one clean record must not conceal a contradictory record.
- This code makes **zero** backend/model calls and has **zero** side effects; Skill readiness, policy execution, provenance attestation, independent engineering qualification, Decision/Action/Outcome handling and enterprise integration remain separate CEPIO gates.

## K-201 synthetic reference checks

`tests/test_competence_activation_ic1.py` uses invented fixture identifiers and requirements such as condition signal, maintenance history and operating context.

- **Evidence present:** returns `CANDIDATE` only—never a compressor diagnosis.
- **Maintenance evidence missing:** returns `BLOCKED` and names the required evidence.
- **Contradictory/ambiguous identity or validity:** returns `BLOCKED` / `AMBIGUOUS`, not an inferred root cause.
- **Wrong tenant, wrong asset, unauthorized source or unauthorized asset:** fails closed.
- **Preview/experimental maturity or absent registry evidence:** fails to become a candidate.

Run `pytest -q tests/test_competence_activation_ic1.py` and the repository's relevant CI lane. Passing those checks provides **synthetic contract behavior evidence only**, not model-quality uplift, live source quality, production feature activation or an updated CEPIO scorecard.

## Next proof gates

**IC-2 — Independent uplift.** Before implementation, pre-register an expert-scored comparison (same frozen model, facts, tool access, prompt budget and time cutoff). Include a competent procedural baseline, model + Microsoft context, and the same model/context + CEPIO; use unseen negative cases controlled in protected Labs. Track route selection, missed activations, engineering errors, evidence correctness, necessary/unnecessary abstention, latency/cost and professional utility. No model or additional live-source access is authorized by IC-1.

**IC-3 — Operationally grounded candidate.** Bind admitted context to authenticated equipment identity and authorized enterprise-source snapshots; verify point-in-time provenance, source permissions, staleness, physics applicability and independent Capability Passport. Keep the existing `SkillPreflight` / READY-only dispatch and Decisions/Actions/Outcomes gates authoritative.

**IC-4 — Host-native integration.** Once independently qualified, bind through existing CEPIO REST/MCP surfaces to a supported Microsoft or other approved host. Measure real eligible-task invocation rather than assuming an MCP/plugin connection guarantees automatic tool selection. No second MCP, agent service, authentication boundary or Studio login.

**Non-goals:** new microservice, mutable global competence from customer data, universal auto-ontology, autonomous approval, commercial promise, release status change, new enterprise connector, Azure deployment or paid inference.

## Ownership and change discipline

Core owns this narrow source-neutral selection/reference check. Specialist methods, sealed expert labels, scenario data and independent evaluations remain in Labs. Customer evidence remains customer-controlled. Product release and maturity evidence follow `RELEASE.md`, `docs/roadmap.md` and the governed v1 scorecard independently of PR status.
