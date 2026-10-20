# CEPIO v1.0 completion scorecard

The canonical CEPIO v1.0 maturity score lives in [`config/v1-scorecard.yaml`](../config/v1-scorecard.yaml).

It is a **100-point, evidence-backed product-maturity score** aligned to CEPIO's North Star:

> CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.

The scorecard is not a substitute for product release gates. A release can earn substantial maturity points and still remain unqualified until its explicit release gate is satisfied.

## Current canonical baseline

Evidence snapshot: `a179e9cfc0dbf5e866a6a6aa143eb4290e79918d`, dated **2026-10-20**.

**CEPIO v1.0 completion: 69/100 (69%)**.

| Stage | Earned | Available | Completion |
| --- | ---: | ---: | ---: |
| Foundation / Core | 30 | 30 | 100% |
| v0.5 Platform Portability | 8 | 15 | 53.3% |
| v0.6 Industry IQ v1 | 13 | 15 | 86.7% |
| v0.7 Assurance + Generalization | 8 | 12 | 66.7% |
| v0.8 Enterprise Profiles + Native Deployment | 4 | 10 | 40.0% |
| v0.9 Multi-Enterprise Portability | 1 | 8 | 12.5% |
| v1.0 Production Guarantees | 5 | 10 | 50.0% |
| **Total** | **69** | **100** | **69%** |

The weighting deliberately gives substantial credit to the already-qualified Core, governance, protocol, Industry IQ and generalization foundations while retaining significant weight for proofs that cannot be simulated away: real platform portability, real enterprise deployment, two-enterprise reuse and production guarantees.

## What changed from the historical draft

The earlier unmerged scorecard draft in PR #196 represented an older repository snapshot at 63/100. This canonical baseline is rebuilt from current `main` and counts only evidence that is merged, qualified or present on the pinned main snapshot.

Material evidence now reflected includes:

- Binding Contract v0.1 and provider-neutral conformance on main;
- Drilling NPT provider parity across Synthetic and Fabric-shaped evidence;
- Rig Readiness and Operator Well Delivery Industry IQ on main;
- Skill-to-pack version compatibility and protocol-converged Skill execution;
- governed Domain Onboarding;
- Enterprise Performance specialization and governed Decision proposal;
- secretless Fabric live-proof transport path and approved Azure demo deployment foundations.

A merged implementation is still not automatically equivalent to a release qualification. For example, the Fabric live-proof transport path is merged, but the scorecard does not claim a successful live Fabric environment qualification unless that evidence exists separately.

## Scoring principles

Every gate has a fixed point budget, earned points, status and structured evidence list.

- The total possible score is always exactly 100.
- Every earned point requires independently verifiable scoring evidence.
- Open pull requests may be listed as progress evidence but cannot contribute points.
- `qualified` gates must earn all available points.
- A gate that earns all available points must be marked `qualified`.
- `planned` gates must earn zero points.
- Partial credit requires an explicit `credit_basis` describing the independently verifiable sub-capability already achieved.
- Invalidated or regressed evidence must reduce the score through a governed PR.
- Generic infrastructure earns maturity points only when it proves a concrete CEPIO operating-intelligence, portability, governance or enterprise requirement.
- Customer-confidential or protected Industry IQ details must not be copied into the public scorecard; safe references may be used instead.

See [`docs/governance/v1-scorecard-governance.md`](governance/v1-scorecard-governance.md) for the authority and change-control contract.

## Calculator

Validate the canonical scorecard:

```bash
python scripts/v1_scorecard.py --check
```

Render a Markdown dashboard:

```bash
python scripts/v1_scorecard.py
```

Emit machine-readable JSON:

```bash
python scripts/v1_scorecard.py --json
```

The validator fails closed for inconsistent weights, score/evidence mismatches, partial credit without a basis, invalid baseline commits, or attempts to count open/unqualified evidence.

## Daily roadmap reporting

Scheduled or manual roadmap reporting should **read** the canonical scorecard and compare it with newer merged evidence.

Scorecard drift means merged or invalidated evidence appears to justify a score change while the canonical YAML has not yet been updated. Reporting should surface that drift and propose a governed scorecard PR; it must not silently invent a new canonical score.

A roadmap brief should lead with:

1. `V1.0 completion: X/100 (X%)` from the canonical scorecard;
2. delta versus the previous canonical scorecard revision;
3. stage-by-stage earned/possible points;
4. newly qualified, regressed or materially advanced gates;
5. evidence drift requiring a scorecard PR;
6. the highest-leverage remaining gates.

## North-Star interpretation

The score rewards progress toward **portable Industrial Operating Intelligence**:

- reusable Industry IQ and persona competence;
- evidence, identity, provenance and uncertainty;
- governed Decision / Authority / Action / Outcome paths;
- replaceable platform bindings;
- model/provider independence;
- enterprise specialization without Core forks;
- generalization and assurance;
- multi-enterprise portability;
- production compatibility, security and operations guarantees.

The score deliberately does **not** reward infrastructure complexity for its own sake. CEPIO should become more valuable because it understands and governs more industrial work, not because it rebuilds capabilities already supplied by Fabric, Cognite, OSDU, cloud infrastructure or frontier models.
