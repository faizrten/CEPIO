# Domain Onboarding Workflow

**North Star:** Domain onboarding grows the independently qualified [Industrial Competence Network](../strategy/industry-iq-product-north-star.md), not just ontology coverage. Cross-domain promotion is governed, never a transfer of customer intelligence by default. Customer-specific domain/profile mappings and derivatives must remain within their authorized enterprise boundary.

CEPIO Domain Onboarding is the governed control-plane workflow for adding an Industry IQ domain without turning each vertical into a bespoke implementation.

## Flow

`REQUESTED -> SCOPED -> BENCHMARKED -> BASELINED -> GAP_ANALYZED -> QUALIFYING -> QUALIFIED -> GENERALIZATION_REVIEW -> RELEASE_CANDIDATE -> RELEASED`

The workflow is defined in `workflows/domain-onboarding-v0.1.yaml`; policy is defined separately in `policies/domain-onboarding-v0.1.yaml`.

## What is governed

A run must establish:

- repository-bounded archetype, persona, standards and competency artifacts;
- a frozen competency benchmark;
- an untouched semantic baseline against the current CEPIO ontology;
- complete classification of every true gap as `CORE`, `COMMON`, `DOMAIN`, `MAPPING`, `PROFILE`, or `REJECT`;
- semantic qualification with no critical failures;
- deterministic runtime-evidence coverage;
- an explicit human Generalization Review before any promotion or release.

CI can qualify evidence but cannot approve promotion or release.

## Reference run

The initial canary is `generalization/domain-packs/refinery-reference-v0.1.yaml`, which reuses the already-qualified Refinery operating abstraction.

Run from the repository root:

```bash
PYTHONPATH=src python scripts/run_domain_onboarding.py \
  --manifest generalization/domain-packs/refinery-reference-v0.1.yaml \
  --json-out domain-onboarding-report.json \
  --fail-on-blocked
```

A successful v0.1 run ends at `GENERALIZATION_REVIEW` with status `READY_FOR_HUMAN_REVIEW`.

See `docs/domain-onboarding-workflow.md` for the full contract, policy gates, manifest format and GitHub Actions instructions.
