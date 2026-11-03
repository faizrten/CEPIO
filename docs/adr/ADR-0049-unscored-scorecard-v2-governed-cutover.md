# ADR-0049: Keep scorecard v2 rubric unscored until independent evidence cutover

**Status:** Proposed (2026-11-03); effective only when governed PR qualifies.  
**Decision owner:** CEPIO product/governance.  
**Classification:** PUBLIC architecture/metric-governance decision.  
**Related:** [canonical v1 scorecard](../../config/v1-scorecard.yaml), [v1 governance](../governance/v1-scorecard-governance.md), [v2 candidate rubric](../../config/v2-scorecard-rubric.yaml), [v2 crosswalk](../../config/v2-scorecard-crosswalk.yaml), [v2 migration governance](../governance/v2-scorecard-migration.md).

## Context

The evidence-backed current score of 69/100, pinned on 2026-10-20, gives 30 points to Foundation/Core and 15 to Industry IQ. CEPIO's adopted North Star now prioritizes independently qualified industrial competence, enterprise/tenant sovereignty, professional user value, evidence-backed decision outcomes and measured AI uplift against a paired non-CEPIO baseline. That is a structural scoring change, not routine progress.

Existing release manifests and explicit gates are authoritative for release, irrespective of aggregate score. OEDA learnings support capability-centric rather than infrastructure-centric evaluation, but do not provide v2 CEPIO qualification evidence.

## Decision

1. Introduce a **seven-dimension, 100-point candidate rubric**: Core 10, Industry IQ 25, Independent Assurance 20, Live Integration 15, Sovereign Compounding 10, Production 10, Professional Value 10.
2. Explicitly set `canonical: false`, `status: proposed_unscored` and `official_v2_score_available: false`. The rubric contains **no earned points**.
3. Preserve v1 original 69/100 score, source YAML and validator. Record a one-to-many traceability crosswalk for all 34 old gates, but **forbid automatic point transfer** or direct v1–v2 numerical deltas.
4. Each future v2 earned point requires a gate-level proof meeting a declared evidence tier and independent verification. Open PRs, synthetic tests portrayed as field observations, or unverified model output never qualify a live or field tier.
5. Hold safety, identity/shift, permit-scope, unauthorized Action, missing-source, tenant leakage and critical security failures as **hard release blockers**, independent of any numerical score.
6. Require probabilistic quantitative and qualitative reservoir uncertainty rather than false deterministic confidence.
7. A **separate** subsequent high-risk PR will independently reassess every v2 gate, add a scored canonical v2 manifest, freeze a supporting Git commit, validate all credit and modify dashboard/reporting only after approval and merge.
8. Protect public Core versus private CEPIO-Labs and customer IP boundaries. Cite only safe attestation references for protected tests.

## Options considered

- **Keep old weights forever:** protects time series but obscures differentiated Industry IQ and professional usefulness. Rejected.
- **Directly replace 69 with a newly weighted score:** fastest but fabricates comparability and risks counting implementation as verified field competence. Rejected.
- **Two-stage unscored rubric, then independent qualification cutover:** preserves historical integrity, auditability and release authority. **Selected.**

## Consequences

The new rubric may produce a significantly different numerical score than 69 on legitimate re-assessment; this is a methodological reset, **not an actual regression or improvement by itself**. The candidate rubric does not unlock production release, modify code behavior, authorize new credentials, spend money or prove users received value. It creates a reviewable contract for gathering that evidence.

## Validation and governance controls

- `python scripts/v1_scorecard.py --check` retains the v1 69/100 baseline.
- `python scripts/v2_scorecard.py --check` enforces 100 candidate points, fixed weights, 23 acceptance-gated criteria, evidence tiers, all 34 exact legacy gates, complete crosswalk and no earned score.
- `pytest -q tests/test_v1_scorecard.py tests/test_v2_scorecard.py` contains adversarial mutation tests for schema, credit transfer, weights, old evidence, crosswalk mapping and probabilistic reservoir doctrine.
- Full CI, code quality, security, IP publication review and human governance gates remain enforced. No bypass or weakened production control.
- A separate reviewed evidence-based cutover PR is mandatory; a merge of this ADR is not itself the cutover.

## Reversal

If candidate qualification thresholds prove unsuitable, revise the candidate via a new governed PR without rewriting historical score evidence. If a v2 scored cutover already occurs, corrections/regressions must follow the new scored baseline governance, not restore or rewrite old v1 history.
