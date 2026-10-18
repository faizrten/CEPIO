# CEPIO v1.0 completion scorecard

The canonical CEPIO v1.0 maturity score lives in `config/v1-scorecard.yaml`.

It is a **100-point evidence-backed score**, not a substitute for product-version release gates. A release can have substantial maturity points and still remain unqualified until its explicit release gate is satisfied.

## Current baseline

As of 2026-10-18, the evidence-backed baseline is **63/100 (63%)**.

| Stage | Points earned | Points available |
| --- | ---: | ---: |
| Foundation / Core | 30 | 30 |
| v0.5 Platform Portability | 7 | 15 |
| v0.6 Industry IQ v1 | 10 | 15 |
| v0.7 Assurance + Generalization | 7 | 12 |
| v0.8 Enterprise Profiles + Native Deployment | 3 | 10 |
| v0.9 Multi-Enterprise Portability | 1 | 8 |
| v1.0 Production Guarantees | 5 | 10 |
| **Total** | **63** | **100** |

The weighting intentionally recognizes that v0.1-v0.4 and multiple later runtime/security foundations are already implemented, while retaining substantial weight for the proofs that cannot be simulated away: platform portability, real enterprise deployment, multi-enterprise reuse and production qualification.

## Scoring rules

Every gate has a fixed point budget, earned points, status and evidence list.

- Earned points require explicit evidence.
- `qualified` gates must earn all available points.
- `planned` gates must earn zero points.
- Partial credit is allowed only for independently verifiable sub-capabilities.
- Open PRs may document implementation progress but are not equivalent to merged or release-qualified capability.
- Customer-confidential or protected Industry IQ details must not be copied into the public scorecard.
- Stage totals and the full score must remain internally consistent and equal exactly 100 possible points.

Changes to earned points should be made through governed PRs with the evidence updated in the same change.

## Calculator

Validate the scorecard:

```bash
python scripts/v1_scorecard.py --check
```

Render a Markdown dashboard:

```bash
python scripts/v1_scorecard.py
```

Emit machine-readable JSON for scheduled reporting:

```bash
python scripts/v1_scorecard.py --json
```

The calculator fails closed when the scorecard is internally inconsistent or when progress is claimed without evidence.

## Daily report contract

The personal `CEPIO Roadmap Daily` report should lead with the canonical score and then check the latest project/GitHub evidence for **scorecard drift**.

Scorecard drift means new merged/qualified evidence appears to justify a point change but the canonical scorecard has not yet been updated through a PR. The scheduled report should call this out rather than silently inventing a new canonical score.

The daily block should contain:

1. `V1.0 completion: X/100 (X%)`, plus change since the prior canonical score;
2. stage-by-stage earned/possible points;
3. newly completed, regressed or materially advanced gates;
4. scorecard drift requiring a scorecard PR;
5. the three highest-leverage next gates.

## North-Star interpretation

Points reward progress toward **portable industrial operating intelligence**:

- reusable Industry IQ;
- evidence, identity and provenance;
- governed Decision / Authority / Action / Outcome;
- platform independence;
- model independence;
- enterprise portability;
- assurance and production guarantees.

Work that primarily recreates generic infrastructure already provided by Fabric, Cognite, OSDU or frontier-model platforms should not receive product-maturity points unless it is required by a concrete CEPIO contract or enterprise proof.
