# Scorecard v2 migration governance — non-scoring first cut

CEPIO's historical v1.0 scorecard remains canonical and immutable for this change. The v2 rubric is a **candidate weighting system** that requires a **separate scored-evidence cutover**.

## Authority and states

- `config/v1-scorecard.yaml`: sole published numerical score (69/100, pinned 2026-10-20) until cutover.
- `config/v2-scorecard-rubric.yaml`: candidate 100-point weights and gate-level qualification thresholds; explicitly `canonical: false`, no earned points.
- `config/v2-scorecard-crosswalk.yaml`: exact, complete 34-gate legacy map; no transfer of earned points.
- Scored v2 authority **does not exist yet**. A later governed, evidence-reviewed PR must create the scored artifact rather than changing the meaning of the old v1 baseline.
- `RELEASE.md` / release gate documentation always outrank scorecard points for release eligibility. v0.5 CONNECT remains incomplete absent live source/writeback qualification.

## Separation-of-duties acceptance for v2 scored cutover

Before a second PR may claim a numerical score it must:

1. Bind each candidate gate to independently located, versioned and rights-permitted evidence.
2. Record exact evidence tier: synthetic, independently evaluated offline, live source or field validated.
3. Prove the gate acceptance contract in the frozen scope; open PRs, sample data and unverified source claims earn no credit.
4. Document partial credit only where independently qualifiable sub-capabilities justify an explicit fraction.
5. Preserve negative controls, uncertainty calibration and safe abstention; reservoir claims are probabilistic.
6. Evaluate the actual security/isolation, issued-permit semantics, identity/shift and Action-authority hard blockers.
7. Provide `v1 old score / v2 reassessed score` *side-by-side*, **never** a misleading improvement/regression delta between different methodologies.
8. Keep proprietary CEPIO-Labs evidence and tenant/customer data out of public GitHub; use sanitized attestation IDs and verification rights.
9. Validate a new scored schema, total exactly 100, score baseline pinned to a real commit, consistent earned/possible/status and regressions.
10. Pass repository CI, governance, security and required reviewer gates before redirecting scheduled reports.

The first PR changes no Azure subscription, inference budget, deployment permissions, customer licensing or published product release.
