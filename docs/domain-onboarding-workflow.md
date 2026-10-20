# CEPIO Domain Onboarding Workflow v0.1

## Purpose

Domain Onboarding is the first CEPIO control-plane workflow for turning a new Industry IQ domain into a governed, testable package. It operationalizes the pattern proven through Drilling Contractor, Refinery/Process Manufacturing and Subsurface work:

`scope -> freeze competency benchmark -> baseline existing CEPIO -> classify true gaps -> qualify semantics/runtime -> generalization review -> release`

The workflow is fail-closed. CI may establish evidence and move a run to `GENERALIZATION_REVIEW`; CI does **not** approve semantic promotion or release.

## Canonical states

`REQUESTED -> SCOPED -> BENCHMARKED -> BASELINED -> GAP_ANALYZED -> QUALIFYING -> QUALIFIED -> GENERALIZATION_REVIEW -> RELEASE_CANDIDATE -> RELEASED`

Policy failures transition to `BLOCKED`. Generalization review may transition to `REJECTED`. Released domains may later transition to `DEPRECATED` under an explicit gate.

The declarative state machine is `workflows/domain-onboarding-v0.1.yaml`.

## Policy v0.1

`policies/domain-onboarding-v0.1.yaml` currently requires:

- a frozen competency benchmark before baseline execution;
- complete classification of every current semantic gap;
- gap dispositions limited to `CORE`, `COMMON`, `DOMAIN`, `MAPPING`, `PROFILE`, or `REJECT`;
- 100% semantic-check pass rate for qualification;
- zero failed critical competencies;
- a runtime evidence suite;
- 100% runtime coverage;
- human review at `GENERALIZATION_REVIEW` and `RELEASE_CANDIDATE`.

These thresholds are policy, not hard-coded workflow semantics, and can evolve by policy version.

## Domain manifest

A domain run is driven by a repository-relative manifest. The first reference pack is:

`generalization/domain-packs/refinery-reference-v0.1.yaml`

It binds the workflow to the existing Refinery/Process Manufacturing archetype, persona pack, standards registry, frozen operating-abstraction competency pack and runtime evidence suite.

A new domain manifest follows this shape:

```yaml
id: mining-domain-onboarding-v0.1
version: "0.1"
domain: mining
name: Mining reference onboarding
mode: new-domain
adjacent_domains: [industrial-common]
artifacts:
  archetype: generalization/archetypes/mining-v0.1.yaml
  personas: generalization/personas/mining-v0.1.yaml
  standards: generalization/standards/mining-references-v0.1.yaml
  competency: generalization/competency/mining-v0.1.yaml
  gap_triage: generalization/gaps/mining-v0.1.yaml
  runtime_suite: generalization/runtime/mining-v0.1.yaml
```

`gap_triage` is optional when the frozen baseline has no semantic gaps. If gaps exist and no accepted triage pack is supplied, the workflow blocks.

## Run locally

From the repository root:

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=src python scripts/run_domain_onboarding.py \
  --manifest generalization/domain-packs/refinery-reference-v0.1.yaml \
  --json-out domain-onboarding-report.json \
  --fail-on-blocked
```

A successful reference run should terminate at:

```text
GENERALIZATION_REVIEW
status: READY_FOR_HUMAN_REVIEW
```

That is intentional. A green workflow means the domain is qualified for architecture/generalization review; it does not mean CEPIO has automatically promoted or released the domain.

## GitHub Actions

The workflow `.github/workflows/domain-onboarding.yml` runs on relevant pull requests and exposes a manual `workflow_dispatch` trigger once present on the default branch.

For a manual run:

1. Open **Actions** in the CEPIO repository.
2. Select **CEPIO Domain Onboarding**.
3. Choose **Run workflow**.
4. Supply the repository-relative domain manifest, or keep the Refinery reference manifest.
5. Inspect the uploaded `domain-onboarding-report.json` evidence artifact.

The JSON report contains the workflow transition history, semantic baseline, gap classification summary, runtime qualification evidence, domain delta and next required human gate.

## Evidence and immutability

The semantic baseline reuses the deterministic Generalization Harness. It records the frozen batch hash and ontology hash. Runtime qualification reuses CEPIO runtime-evidence coverage and its fail-closed operator-evidence gate.

The benchmark must not be edited merely to turn a failure into a pass. A changed benchmark is a new benchmark version and should be treated as new workflow evidence.

## v0.1 boundary

v0.1 automates repository-artifact governance through `GENERALIZATION_REVIEW`. It does not yet:

- synthesize domain personas or competency questions;
- infer gap dispositions with an LLM;
- automatically modify ontology modules;
- automatically promote DOMAIN semantics to COMMON/Core;
- automatically approve generalization or release;
- persist the control-plane state as a long-running Kinetic workflow instance.

Those are deliberate boundaries. The state and policy contracts are structured so later CEPIO Workflow/Kinetic bindings can preserve the same gates rather than invent a second methodology.
