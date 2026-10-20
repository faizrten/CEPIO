# CEPIO v1.0 scorecard schema

The canonical scorecard is YAML at `config/v1-scorecard.yaml`. This document defines the human-readable schema contract enforced by `scripts/v1_scorecard.py` and `tests/test_v1_scorecard.py`.

## Root fields

| Field | Type | Rule |
| --- | --- | --- |
| `schema_version` | string | Non-empty scorecard schema identifier. |
| `scorecard_version` | string | Non-empty version of the canonical scoring model. |
| `product` | string | Product identifier; currently `CEPIO`. |
| `target_release` | string | Completion target; currently `v1.0`. |
| `canonical` | boolean | Must be `true`. |
| `north_star` | string | Product North Star used to interpret what deserves maturity credit. |
| `scoring` | mapping | Global scoring metadata and governance rules. |
| `stages` | list | Fixed weighted roadmap stages. |

## `scoring`

Required fields:

- `total_points`: integer and exactly `100`;
- `baseline_date`: non-empty date string;
- `baseline_commit`: exact lowercase 40-character git SHA;
- `baseline_points`: integer equal to the sum of all stage/gate earned points;
- `governance_document`: path to the scorecard governance contract;
- `rules`: non-empty list of unique `{id, text}` rule mappings.

`baseline_commit` intentionally pins the evidence snapshot. Work merged after that commit is scorecard drift until a governed scorecard revision incorporates it.

## Stage

Each stage contains:

```yaml
- id: v0.5
  name: Platform Portability
  release_scope: v0.5
  points: 15
  earned: 8
  gates: [...]
```

Rules:

- stage IDs are unique;
- `points` is a positive integer;
- `earned` is an integer from zero through `points`;
- sum of gate `points` must equal stage `points`;
- sum of gate `earned` must equal stage `earned`;
- sum of all stage `points` must equal exactly 100.

## Gate

Each gate contains:

```yaml
- id: P2
  title: Fabric-native observation/evidence plane with preserved provenance
  points: 3
  earned: 2
  status: in_progress
  credit_basis: >-
    Fabric provider parity is merged, while successful live environment qualification remains open.
  evidence: [...]
```

Allowed status values:

- `planned`;
- `in_progress`;
- `qualified`.

Rules:

- gate IDs are globally unique;
- gate points are positive integers;
- earned points are between zero and the gate point budget;
- a `qualified` gate must earn all points;
- a fully earned gate must be `qualified`;
- a `planned` gate must earn zero points;
- partial credit (`0 < earned < points`) requires a non-empty `credit_basis`;
- any earned points require at least one scoring evidence item.

## Evidence

Evidence is deliberately structured rather than free-form text.

```yaml
evidence:
  - kind: pull_request
    ref: "PR #219"
    state: merged
    counts_toward_score: true
    claim: Same Industry IQ capability preserves semantics across Synthetic and Fabric evidence.
```

Required evidence fields:

| Field | Meaning |
| --- | --- |
| `kind` | Evidence class, for example `pull_request`, `repository`, or `protected_reference`. |
| `ref` | Stable human-locatable reference. |
| `state` | Evidence lifecycle state. |
| `counts_toward_score` | Whether the evidence may support earned points. |
| `claim` | Exact product capability supported by the evidence. |

Only these evidence states may count toward the score:

- `merged`;
- `qualified`;
- `main`.

Other states may be present for visibility but must use `counts_toward_score: false`. The canonical example is an open PR:

```yaml
- kind: pull_request
  ref: "PR #238"
  state: open
  counts_toward_score: false
  claim: Active implementation work; no canonical points until merged.
```

This prevents roadmap optimism from becoming score inflation.

## Partial-credit discipline

`credit_basis` is not a general status note. It must identify the independently verifiable portion already achieved and the substantive proof still missing.

Good:

> Provider-neutral identity and Synthetic/Fabric parity are qualified; Cognite parity remains unproven.

Bad:

> Work is going well.

The validator can prove that a basis exists, but reviewers remain responsible for judging whether the fraction is materially justified.

## Score changes

Normal score changes modify:

- gate `earned`;
- gate `status` where appropriate;
- gate `credit_basis`;
- evidence entries;
- stage `earned`;
- `scoring.baseline_points`;
- `scoring.baseline_date`;
- `scoring.baseline_commit`.

Point budgets should not change during routine progress updates.

Reweighting requires explicit product-governance rationale because it changes the interpretation of historical scores.

## Machine outputs

`python scripts/v1_scorecard.py --json` emits:

- canonical scorecard version;
- baseline date and commit;
- total earned/possible points;
- completion percentage;
- stage completion;
- gate status/remaining points;
- largest remaining gates.

The Markdown renderer exposes the same validated source. No second score calculation is maintained elsewhere.
