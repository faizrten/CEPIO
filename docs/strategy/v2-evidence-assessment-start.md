# CEPIO v2 — public evidence qualification triage (unscored)

**Status:** Evidence-candidate inventory only — NOT ASSESSED and **not a v2 completion score**.  
**Snapshot:** public `faizrten/CEPIO` main at `19e5bd947b9eed507e8ecb795b485439f0d00d28` (2026-11-03).  
**Governing work:** [Issue #326](https://github.com/faizrten/CEPIO/issues/326).  
**Inputs:** [v2 rubric](../../config/v2-scorecard-rubric.yaml), [23-gate evidence inventory](../../config/v2-evidence-inventory.yaml), [v1-to-v2 crosswalk](../../config/v2-scorecard-crosswalk.yaml).  
**Validation:** `python scripts/v2_evidence_inventory.py --check`; `pytest -q tests/test_v2_evidence_inventory.py`.

## What the audit does and does not mean

A public merged PR or source file is a useful **evidence lead**. It can demonstrate implementation and synthetic conformance but does not, by itself, prove independent expert qualification, live industrial source attestations, production SLOs or attributable customer value.

The inventory accounts for **all 23 candidate gates**, each with a source lead (where available), scope limitation and the specific next proof necessary. It contains **no earned points, no partial credits and no claimed qualified states**. No customer/prospect material or protected evaluator logic was used.

The v1 historical canonical **69/100** remains the sole official score. The proposed v2 rubric has a 100-point budget but no official score. These values must never be subtracted to create a fictitious regression.

## Initial observed evidence leads

The strongest public source leads are the v0.4/Core contract, deterministic onboarding and Skill/pack composition, the governed Action/Outcome conformance path, and synthetic provider-neutral parity. Recent merged additions include:

- [PR #316](https://github.com/faizrten/CEPIO/pull/316): host-bound, non-executing assurance receipts; explicitly development-only, not live source signatures.
- [PR #319](https://github.com/faizrten/CEPIO/pull/319): synthetic cross-domain K-201/Reservoir R3 negative controls; not measured independent expert uplift.
- [PR #322](https://github.com/faizrten/CEPIO/pull/322): offline Copilot-harness comparison tooling; not a live Foundry G1 qualification.
- [PR #330](https://github.com/faizrten/CEPIO/pull/330): source-to-state conflict assessment; read-only/non-authoritative, not permission to operate a real asset.
- [PR #238](https://github.com/faizrten/CEPIO/pull/238): governed compounding registry/promotion mechanics; rights-cleared, independently qualified promotion must still be separately demonstrated.

These technical advances **can be examined for valid v2 credit** after assessing actual acceptance criteria. The list is not a blanket approval.

## Highest-value qualification work

1. **Assurance and IQ competence** (45 of 100 possible candidate points): pre-register professional tasks and blind/independent adjudication, matched model/data/tools comparison with versus without CEPIO, sealed negative tests, calibrated uncertainty, safe abstention and critical-error rates. In reservoir work, quantify and qualitatively justify probabilistic outcomes; do not reward false deterministic certainty.
2. **Live integration and action** (15 points): prove one asset with three meaningful authoritative domains (including SAP and PI as relevant), authenticated policy, traceable evidence, a permitted source Action, readback, idempotency and a reconciled Outcome. Synthetic Fabric parity or hosted transport scaffolds do not earn live credit.
3. **Sovereignty and production** (20 points): independent tenant/derivative knowledge leakage negatives, rights-controlled promotion, vulnerability/isolation qualifications, tested restore/DR and independently operated deployment.
4. **Professional experience and outcomes** (10 points): Rig Manager to Operator Well Delivery, reliability, and reservoir persona workflows validated for correct shifts, permits, contradictory evidence/status presentation, reading burden, decision accuracy and consented attributable value.
5. **Core operating contract** (10 points): recheck prior v0.4 evidence against v2 gate acceptance and test any new conflict/state logic without assuming the earlier 30 Foundation points transfer automatically.

## Evidence decision contract for the next scored PR

An assessor must review each gate's versioned evidence against its minimum tier, exact acceptance tests, safety/sovereignty blockers and any explicitly justified partial-credit sub-capability. A proposed numeric score should be built from individually awarded points and independent attestations, with negative outcomes retained and a frozen baseline commit.

Do not create or activate an official v2 scored manifest or change the daily CEPIO score until a separate governed PR is independently qualified and merged. No customer exports, Azure changes, paid inference or source writeback are authorized by this inventory.
