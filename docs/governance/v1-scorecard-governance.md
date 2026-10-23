# CEPIO v1.0 scorecard governance

## Purpose

The v1.0 scorecard is the canonical numerical statement of CEPIO product maturity on the path to v1.0. It exists to prevent roadmap progress from becoming an informal narrative that changes faster than its evidence.

The canonical source is:

`config/v1-scorecard.yaml`

The repository history is the audit trail.

## Authority model

The following hierarchy is deliberate:

1. **Release gates and release manifests** are authoritative for whether a CEPIO product version is qualified.
2. **`config/v1-scorecard.yaml`** is authoritative for the numeric v1.0 completion percentage and stage/gate maturity points.
3. **Roadmap and wiki documentation** explain intent, sequencing and context but must not invent a different numerical completion score.
4. **Scheduled reports and dashboards** are read-only projections of the canonical scorecard plus evidence-drift detection.

A 100/100 score would not by itself authorize a release if an explicit release gate remained unqualified.

## Fixed 100-point model

The scorecard contains exactly 100 available points across:

- Foundation / Core;
- v0.5 Platform Portability;
- v0.6 Industry IQ v1;
- v0.7 Assurance + Generalization;
- v0.8 Enterprise Profiles + Native Deployment;
- v0.9 Multi-Enterprise Portability;
- v1.0 Production Guarantees.

Weights are structural product-governance decisions. They should change rarely because reweighting changes the meaning of historical scores.

A reweighting PR must:

- state why the previous weighting no longer represents the North Star;
- show the before/after score and stage distribution;
- explain whether historical comparisons remain meaningful;
- preserve an exact 100-point total;
- receive the same repository governance and qualification as other material roadmap changes.

Routine feature progress must update **earned points**, not silently alter weights.

## Evidence contract

Every earned point requires structured evidence with:

- `kind` — repository artifact, pull request, protected reference or equivalent;
- `ref` — a stable human-locatable reference;
- `state` — evidence lifecycle state;
- `counts_toward_score` — explicit boolean;
- `claim` — the exact capability the evidence supports.

Only evidence in one of these states may count toward points:

- `merged`;
- `qualified`;
- `main`.

An open PR may be referenced with `counts_toward_score: false` to make progress visible, but it may not increase the canonical score.

The scorecard must never infer capability solely from an issue title, roadmap intention, unmerged branch, local experiment or verbal statement.

## Partial credit

Partial credit is allowed only when a gate contains independently verifiable sub-capabilities and the achieved subset materially reduces the remaining risk.

A partially earned gate must include `credit_basis` describing:

- what is already proven;
- what remains unproven;
- why the earned fraction is justified.

Partial credit must not be used to make a roadmap look healthier. Where the remaining proof is the substantive proof—for example a real enterprise deployment or production live-binding qualification—credit should remain conservative.

## Qualified and planned states

A gate marked `qualified` must earn all available points.

A gate that earns all available points must be marked `qualified`.

A gate marked `planned` must earn zero points.

These rules ensure score and lifecycle state cannot diverge.

## Score regression

The score is allowed to move down.

A regression is required when previously counted evidence is invalidated by, for example:

- a contract is withdrawn or superseded without an equivalent replacement;
- a qualification is shown to be invalid;
- compatibility or security evidence no longer holds;
- an architectural change removes a previously counted capability;
- a production or portability proof is reclassified after stronger evidence shows it was overstated.

The correcting PR must reduce the affected gate and update the evidence record. Historical repository revisions preserve the prior score for audit.

## Baseline pinning

Every canonical scorecard revision includes:

- `baseline_date`;
- `baseline_commit`;
- `baseline_points`.

`baseline_commit` is the exact 40-character commit SHA whose merged evidence supports the score. A scorecard PR may itself land after that snapshot; this is expected. Newer work should not be counted until the YAML is deliberately refreshed.

This makes scorecard drift detectable instead of ambiguous.

## Evidence drift

Evidence drift occurs when repository state and the canonical scorecard diverge materially.

Examples:

- a merged PR satisfies the remaining portion of a partially earned gate;
- a new real deployment qualifies a previously planned enterprise gate;
- a counted capability is superseded or invalidated;
- a new cross-platform or multi-model proof materially changes a portability/assurance gate.

Automation may detect and report drift. It may open or recommend a scorecard PR. It must not silently mutate earned points on `main`.

## North-Star anti-gaming rule

A capability earns score only when it advances CEPIO's portable Industrial Operating Intelligence North Star.

The scorecard should reward:

- reusable Industry IQ;
- industrial competency and operating questions;
- evidence/provenance/uncertainty;
- governed decisions and actions;
- replaceable platform bindings;
- provider/model portability;
- enterprise specialization without Core forks;
- assurance/generalization;
- real enterprise adoption;
- production compatibility, security and operational guarantees.

The scorecard should not reward generic infrastructure duplication merely because it increases code volume. Rebuilding functionality already supplied by Fabric, Cognite, OSDU, Azure or frontier-model platforms earns no points unless that work is required to prove a concrete CEPIO contract or release gate.

## Public / protected / customer-confidential boundary

The public scorecard may reference protected CEPIO-Labs evidence at a safe abstraction level, for example a benchmark or Skill-package identifier. It must not copy:

- unseen evaluation corpora;
- evaluator answer keys;
- proprietary customer procedures or thresholds;
- customer mappings or data;
- confidential learned behavior;
- credentials or environment secrets.

Customer-confidential evidence may justify an internal release decision, but the public scorecard must use a sanitized evidence reference or a public qualification statement rather than exposing the underlying material.

## Sovereignty and compounding measures (non-scoring)

The North Star now explicitly includes globally compounding *qualified* industrial competence and independently sovereign customer intelligence. Use two supplemental reporting dimensions: **Industrial Competence Compounding** (independent-domain coverage, holdout results, cross-domain regression, reuse efficiency) and **Intelligence Sovereignty Assurance** (permitted-use provenance, tenant isolation negative tests, absence of unauthorized sharing, contribution rights reviews and derivative leakage checks).

These metrics are **not additional score points**. The canonical score remains exactly 100 possible points; its stage weights and earned points change only through the evidence/reweighting workflow above. A privacy, customer-IP, cross-tenant isolation or human-authority hard-gate failure must block its affected release regardless of score. Unknown, untested and proposed mechanisms must never be reported as passing or qualified. Do not publish confidential telemetry or source materials to prove these indicators; cite authorized attestations.

## Change workflow

A normal score update follows:

`evidence changes -> scorecard drift detected -> scorecard PR -> validator/tests -> normal governance/CI -> merge -> new canonical baseline`

The PR should state:

- old score and new score;
- gates changed;
- evidence added/removed;
- whether any stage weights changed;
- whether any product release gate changed independently of the score.

## Validation

The canonical validator is:

```bash
python scripts/v1_scorecard.py --check
```

Repository tests must fail if:

- total available points are not exactly 100;
- stage and gate totals disagree;
- baseline points do not equal earned points;
- earned points lack scoring evidence;
- open/unqualified evidence is marked as counting;
- partial credit lacks a credit basis;
- qualified/planned status conflicts with earned points;
- the baseline commit is not an exact git SHA.

This validation is part of the repository test suite, so the scorecard cannot become structurally inconsistent without failing normal qualification.
