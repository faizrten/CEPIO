# Auto-Ontology reinforcement increment

Date: 2026-11-11. Status: development; no deployment or qualification claim.

## Outcome and boundaries

Embed Auto-Ontology as a replaceable semantic provider in CEPIO's existing
lifecycle. Reinforcement of existing ontology is a required outcome: resolve
existing IRIs first, deepen approved definitions, preserve units/context and
bind evidence requirements to reusable methods. New concept count is not success.
Shared Core remains thin. Industry extensions and tenant mappings retain their
own authority; customer knowledge cannot silently promote into shared knowledge.

## Verified starting points

Inspection base: CEPIO `be0f41464c74087804d5bfde0cf3908362920fcb`.
Upstream API inspection pin: NVIDIA/auto-ontology
`fc43a82600e18b19d159c52023f54f5572f537ac`.

| Existing artifact | Reuse |
| --- | --- |
| `ontology-modules.yaml`, `ontologies/*.ttl` | Canonical modular vocabulary and IRIs |
| `src/cepio/platform_bindings.py` | EvidenceEnvelope, manifest, explicit host registration |
| `src/cepio/domain_onboarding.py` | Frozen benchmark, gap triage and human review lifecycle |
| `src/cepio/capability_registry.py` | Evidence-backed promotion and profile/global boundaries |
| `scripts/run_compounding_intelligence.py` | Existing compounding and regression workflow |
| `src/cepio/accc_runtime_binding.py` | Host-derived identity and admission pattern |
| `tests/test_drilling_npt_binding_parity_v05.py` | Existing same-method/different-provider regression |
| `examples/accc_k201_offline.py` | Candidate K-201 investigation fixture |

Protected methods, evaluation truth and customer mappings belong in Labs or the
customer boundary. No protected fixture is copied into public Core. Labs is
visible through the GitHub connector; authenticated shell cloning is unavailable.

## Milestones

| Gate | Deliverable | Current status |
| --- | --- | --- |
| M1 | Inventory, frozen datasets/questions/oracles and evaluation contract | Inventory and contract drafted; held-out corpus, model/budgets and hashes remain open |
| M2 | Host-bound semantic retrieval and traceable evidence path | Offline HTTP contract increment; live source and harness dispatch remain open |
| M3 | Reconcile, review, version and roll back useful enrichment | Open; reuse onboarding/promotion controls |
| M4 | Same method works on a differently structured dataset | Open; NPT parity is a regression guard, not new Auto-Ontology proof |
| M5 | Two-arm comparison meets frozen acceptance thresholds | Open; no inference performed |
| M6 | Studio/headless experience and controlled deployment | Open |

## First executable increment

`AutoOntologyTermBinding` implements the existing EvidenceBinding protocol for
`GET /api/terms/{term_id}` on the upstream public gateway. Its envelope contains
unapproved semantic metadata, never physical measurements or engineering truth.
Upstream certification does not become CEPIO approval. Response hashes identify
observed bytes, not authoritative source versions. No versioned-identity
capability is declared and no runtime READY registration is created automatically.

The trusted host must construct this binding per request with:

- an authenticated ActorContext supplier checked on every read;
- an exact tenant and actor, plus an explicit term allowlist;
- a policy callback checking current source-use permission;
- an HTTP client authenticated as that same actor against the approved deployment.

These callbacks are trusted host code, not assertions accepted from a tool caller.
The adapter does not prove client credentials match the CEPIO actor; that binding
is a required live host qualification gate. Tenant partition metadata is a label,
not independent upstream tenant-isolation enforcement. No public route is added.

The adapter refuses redirects, out-of-scope term IDs, wrong principals, denied
permissions, non-200 responses, malformed JSON, mismatched identities and payloads
over 256 KiB. Upstream errors are sanitized. Provider text remains untrusted data;
it must not become instructions, executable SQL or authority in later consumers.

No querying, schema compilation, inference, Kumo upload, canonical ontology
mutation, automatic promotion, deployment or new infrastructure is included.

## Two-arm evaluation contract

Exactly two arms: **LLM only** and **the same LLM + Auto-Ontology + CEPIO**.
The baseline receives the same underlying evidence through neutral read tools or
a complete bounded export; no CEPIO methods or semantic definitions are injected
into the baseline. Freeze the access mode before running. Both arms receive
identical questions and model settings, matched maximum total inference budgets
and tool-time limits. Count all Auto-Ontology model calls in the combined arm;
report compilation/onboarding cost separately and amortized. Store input hashes,
model/deployment revisions, prompts, tool traces, errors and complete costs.

Use separate development and held-out datasets. Freeze expected answers, rubric
and critical errors before inference. Select K-201 and a differently structured
transfer fixture in Labs after inspecting their current contents. Do not invent
evidence of their readiness from earlier conversations. Evaluators must not expose
held-out truth to either arm; blind labels and deterministic checks precede any
reviewer opinion. Report paired outcomes, sample size and uncertainty.

Initial proposed acceptance thresholds, to freeze with the M1 corpus:

- zero critical wrong-asset, unauthorized-use, invalid-unit or unsupported-action errors;
- all previously qualified regression cases pass;
- at least one approved, provenance-backed enrichment reused by an existing method
  on the second schema without method code changes;
- zero unresolved ambiguity silently accepted as an approved mapping;
- at least 10 percentage points improvement in held-out task correctness, with
  a paired confidence interval excluding zero; otherwise report inconclusive;
- no increase in unsupported conclusions; report appropriate abstention separately;
- report p50/p95 latency and full cost; numeric operating ceilings remain open
  until actual model and pilot budgets are established.

These are prospective gates, not achieved results. Mapping precision, duplicate
and conflict rates, review minutes and setup effort are measured separately from
decision quality. Small offline transport tests cannot establish judgement uplift.

## Next integration work

Inspect and freeze Labs fixtures, then implement a reconciliation proposal surface
against canonical CEPIO IRIs. Preserve ambiguity as a review blocker. Feed qualified
proposals into the existing onboarding/compounding lifecycle; retain source rights,
scope and human approval. Add method dependency regression and rollback before any
promotion. Wire the request-scoped binding through existing host admission only
after credential/tenant correspondence is verified. Live work requires a configured
source and bounded inference setup; none is assumed by this increment.

## Reconciliation increment (11 November 2026)

`propose_reconciliation` now consumes an authorized semantic envelope and a
host-approved named-node RDF projection. It returns deterministic candidates for
exact IRIs, local names and English/untyped labels or synonyms. Unique lexical
matches remain proposals; multiple candidates are blocked as ambiguous and absent
matches do not mint new IRIs. Unit, context, rights and engineering applicability
remain review requirements. This deliberately narrow public interoperability
primitive contains no protected matching heuristics or industrial reasoning.

Proposals carry tenant identity, source key, term digest and ontology digest.
Definitions and relationships contribute to the ontology digest; changed meaning
therefore invalidates snapshot identity. Blank-node graphs require an explicit
named-node projection; language fallback and fuzzy matching are not implemented.
The graph and registry are never mutated. This is partial M3 groundwork, not an
approved enrichment, promotion workflow or completed ontology reinforcement proof.

GitHub's initial quality gate found two uncovered constructor rejection paths;
additional identity/allowlist tests now cover them. The two new modules have 100%
statement coverage in targeted offline tests. Full CI remains the merge gate.
Inspection of existing Labs evaluation metadata also found historical multi-arm
protocols and scope-specific inactive model authorization. They must not be reused
as this work's two-arm protocol or as permission to invoke models. A separate
experiment manifest is required; held-out cases and live budget verification
remain open.
