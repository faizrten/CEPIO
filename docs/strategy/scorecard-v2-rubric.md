# CEPIO v1.0 maturity — v2 seven-dimension rubric (candidate)

**Status:** proposed, **unscored**, non-canonical; structural reweighting only.  
**Approved design direction:** 2026-11-03.  
**Current canonical maturity:** 69/100 in `config/v1-scorecard.yaml` (evidence baseline 2026-10-20).  
**Current released product:** v0.4 Developer Preview; v0.5 CONNECT release gate remains open/partial.  
**Normative candidate:** `config/v2-scorecard-rubric.yaml`.  
**Historical traceability:** `config/v2-scorecard-crosswalk.yaml`.  
**Validation:** `python scripts/v2_scorecard.py --check`, `pytest -q tests/test_v2_scorecard.py`.

## Why change the scoring model?

The original v1 rubric is evidence-backed and valid for its original **maturity definition**, but it weights Foundation/Core 30/100 and Industry IQ v1 15/100. Its 69/100 therefore cannot be interpreted as verified professional outcomes, live integration or field readiness. The approved North Star now emphasizes the trusted expert companion, independently qualified Industrial Competence Network, sovereign knowledge, professional workflow value and measurable CEPIO uplift.

A scorecard measures **what has been qualified**, not what is written in a roadmap, what exists in a sample library, or how many infrastructure components have been deployed.

## Proposed 100-point allocation

| Dimension | Candidate budget | Qualifying evidence emphasis |
| --- | ---: | --- |
| Core operating contracts | 10 | Canonical semantics, time, provenance, policy, Decisions, Actions and protocol contracts |
| Industry IQ competence | 25 | Expert-assessed domain/persona competence, cross-domain reasoning, uncertainty and abstention |
| Independent assurance and measured uplift | 20 | Held-out evaluation, matched CEPIO versus non-CEPIO baselines, safety negatives and Capability Passports |
| Live integration and governed industrial outcomes | 15 | Authoritative multi-system context, external write/readback/reconcile and source-provider parity |
| Sovereign intelligence compounding | 10 | Rights-cleared promotions, reuse economics, negative-tested tenant/customer separation |
| Enterprise production readiness | 10 | Security, SLO, backup/restore, recovery, compatibility and clean-room adoption |
| Professional experience and demonstrated value | 10 | Persona-adaptive workflows, expert decision burden and verifiable customer value |
| **Total** | **100** | **No v2 earned points assigned in this PR** |

The 23 candidate gates each have an acceptance contract and a **minimum evidence tier**. Minimum tiers are floors, not promises that a valid sample will automatically qualify a gate. For a complex decision, assurance can require multiple modalities, expert adjudication or a higher tier than the minimum. A PR merge alone never constitutes independent qualification.

## Evidence maturity ladder

1. **Synthetic conformance:** deterministic/unit/contract tests using public synthetic examples. Establishes implementation behavior, not live truth.
2. **Independent offline:** frozen evaluation conducted independently from the candidate; controlled model/tool/data baseline, expert review and unseen negative cases. Establishes only the tested scope.
3. **Live source:** authenticated source-system retrieval/attestation, temporal provenance and, where applicable, external write/readback/reconcile with permitted credentials and audit.
4. **Field validated:** authorized customer operations with attributable outcome measurements, baseline and documented limitations.

Only a later governed scoring assessment may introduce `earned`, `credit_basis`, evidence references and qualification states into a **new canonical scored v2 manifest**. Do not add fake zero/unknown scores to this unscored candidate. Treat **not assessed** as unknown, never zero risk.

## Non-negotiable hard release blockers

No aggregate score overrides unauthorized Actions, unapproved cross-tenant/customer-derived learning, fabricated/wrong-shift identities, wrong-task permits, treating an issued permit as permission to work, unavailable/unverified evidence portrayed as authoritative, or unresolved critical security/isolation findings. These are release blockers independent of point totals.

Reservoir intelligence must be explicitly **probabilistic**, with quantitative distributions and qualitative technical reasoning about uncertainty, missingness and competing hypotheses. Failure to establish a deterministic reservoir result is not by itself incompetence; unsupported deterministic confidence is a failure.

All protected holdouts, domain cases, proprietary Skills and scoring methods remain in CEPIO-Labs. Enterprise material belongs in enterprise-controlled environments. Public evidence may use safe, checkable identifiers/attestations only.

## Evidence-drift triage as of 2026-11-03

This is a **candidate evidence review queue**, not an award of points, not proof of live capability and not an exhaustive repository audit.

| Evidence | Candidate dimensions | What it does and does not establish |
| --- | --- | --- |
| Existing v0.4/Kernel & governance evidence (F1–F6) | CORE, PRODUCTION | Qualifies the prior v1 implementation baseline; must be rechecked against the more specific v2 contract and evidence tier |
| Mainline Drilling/Reliability and governed pack foundations (I1–I5) | IQ, ASSURANCE | Significant pack/runtime conformance; independently evaluated end-user competence and field trust still need specific evidence |
| [PR #316](https://github.com/faizrten/CEPIO/pull/316) | CORE, ASSURANCE, COMPOUND | Merged host-bound in-memory evidence/receipt contract; **not** cryptographic source attestation or durable production audit |
| [PR #319](https://github.com/faizrten/CEPIO/pull/319) | IQ, ASSURANCE | Merged K-201/Reservoir R3 synthetic cross-domain negative regression; **not** measured CEPIO uplift, live source or customer outcome |
| [PR #322](https://github.com/faizrten/CEPIO/pull/322) | ASSURANCE, INTEGRATION | Merged offline Copilot-harness comparison tooling; **not** live G1 identity/Decision persistence qualification |
| [PRs #323–#325](https://github.com/faizrten/CEPIO/pull/325) | CORE, INTEGRATION | Operational object/state work currently proposed in open PRs; **no earned points from unmerged work** |
| Existing synthetic Fabric-provider parity and live-proof path | INTEGRATION | Provider-neutral semantics and available transport path; not yet a separately verified live industrial evidence-and-action loop |
| Customer field outcomes | PROFESSIONAL | **Not assessed here**; consented production/field evidence and an attributable baseline are required |

Four candidate gates have **no direct legacy gate match**: IQ4 (calibrated uncertainty), AS1 (matched uplift), AS4 (Capability Passport), UX2 (expert-reviewed workflow burden). They deliberately represent strategic maturity that was not scored directly before.

## Score comparisons and accountability

**69/100 v1 is historical, not an input for 69/100 v2.** The crosswalk covers all 34 old gates, preserves their individual points and achieved credit, and maps evidence *topics* rather than transferring points. Once independent v2 scoring is complete, report:

- `v1 historical = 69/100` with the exact original baseline/commit;
- `v2 independently reassessed = N/100` with a newly frozen evidence commit and its own gate-level proof;
- `methodology changed; direct numerical delta is not meaningful`;
- changes within v2 over time only after a canonical v2 scored baseline has been approved.

All daily briefs continue reporting the v1 canonical number **until** an independently approved v2 cutover. The new score must not be published merely because the rubric has merged. The released-product gate remains independently governed by `RELEASE.md` and `docs/roadmap.md`.

## Execution plan / two-PR governance

1. **PR 1 — this rubric/crosswalk:** fixed seven-dimensional structure, acceptance criteria, no-score policy, zero automatic credit, safety/sovereignty hard blockers, complete legacy mapping, executable validation and tests. Keep v1 canonical untouched.
2. **PR 2 — evidence reassessment and cutover:** inspect specific merged/public/protected/authorized evidence with independent review; quantify gate-level earned credit, limitations and open live/field proofs; freeze commit; add a *separate* canonical v2 scored YAML plus scoring validator/tests and read-only dashboard rendering; update reporting only on merge. If protected evidence cannot be verified, leave its gate unqualified rather than infer.
3. **Subsequent quarterly rubric changes:** separately reviewed structural PRs with historical comparison, no routine reweighting to make progress appear better.

**No production deployment, infrastructure or paid inference is authorized by a scorecard revision.**
