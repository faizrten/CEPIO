# Capability Registry and Compounding Industrial Intelligence v0.1

## Purpose

CEPIO should become more capable as each domain is onboarded without training on customer data or allowing customer-specific semantics to leak into the global platform. The v0.1 compounding loop makes that behavior explicit and measurable.

The loop is:

```text
Domain Onboarding
  -> Domain Delta
  -> Generalization Review
  -> Capability Promotion
  -> Cross-Domain Regression
  -> Proposed Capability Registry Update
  -> Human Release Review
```

Automation discovers, evaluates and produces evidence. It does not silently promote global capability or publish a domain release.

## Three registries, three responsibilities

CEPIO now has three deliberately different registry concepts:

- **Industry IQ Pack Registry**: what installable Industry IQ functions, decisions and actions are available at runtime.
- **Skill Registry**: which resolved Skill contracts are admitted for execution in the current runtime.
- **Capability Registry**: what CEPIO can claim it knows how to do, where that capability has been proven, its maturity and the evidence supporting the claim.

The Capability Registry is an evidence ledger, not a deployment registry and not a second ontology.

## Capability record

A capability can carry:

- semantic terms and relationships;
- personas and competency references;
- evidence requirements and reasoning patterns;
- Skills, Decisions, authority and policy requirements;
- Industry IQ Pack references and runtime binding patterns;
- uncertainty models;
- validated domains;
- qualification evidence;
- maturity and promotion provenance.

The seed registry at `generalization/capabilities/registry-v0.1.yaml` backfills one conservative Industrial Common capability: `industrial.reliability.condition-work-context`. It is marked `QUALIFIED` only because independent Drilling and Refinery competency and runtime suites already prove the reusable condition-to-equipment-to-work context.

## Customer-data boundary

For `CORE`, `COMMON` and `DOMAIN` capability records, CEPIO rejects:

- evidence explicitly marked customer-specific;
- evidence with `PROFILE` scope;
- evidence paths under `/customers/`.

A customer profile may validate that a capability works in another deployment, and an aggregate validation count may be retained, but the customer's data or profile artifact does not become global capability evidence.

This is evidence-driven generalization, not self-training on customer data.

## Promotion policy

`policies/capability-promotion-v0.1.yaml` requires:

- at least two independent domains;
- target layer `CORE` or `COMMON`;
- 100% survival of the configured cross-domain regression suite;
- no customer-specific evidence as promotion justification;
- explicit human architecture approval.

AI/agent roles are rejected as architecture approvers by the contract.

`workflows/capability-promotion-v0.1.yaml` defines the lifecycle:

```text
CANDIDATE
  -> EVIDENCE_COLLECTED
  -> CROSS_DOMAIN_TESTED
  -> ARCHITECTURE_REVIEW
  -> APPROVED
  -> PROMOTED
```

Policy, regression or human rejection can instead lead to `BLOCKED` or `REJECTED`.

## Cross-domain regression

`generalization/regression/industrial-common-v0.1.yaml` is the first reusable regression suite. It runs independent semantic and runtime-evidence qualification for:

- Drilling Contractor capability benchmark v0.3 / runtime coverage v0.5;
- Refinery Operating Abstraction v0.1 / runtime suite v0.1.

A reusable capability must survive all configured targets before promotion.

## Compounding metrics

The runner emits measurable indicators rather than the vague statement that CEPIO is "getting smarter":

- capability count;
- reusable capability count;
- cross-domain capability count;
- average validated domains per capability;
- qualified-or-better capability count;
- semantic contract reuse rate for the onboarded domain;
- reusable competency coverage rate;
- new semantic gap count and marginal gap rate;
- cross-domain regression survival rate;
- promotion candidate count and promotion rate.

The long-term target is for later domains to start from a progressively higher reuse baseline while requiring less genuinely new semantic and reasoning capability.

## Run locally

```bash
PYTHONPATH=src python scripts/run_domain_onboarding.py \
  --manifest generalization/domain-packs/refinery-reference-v0.1.yaml \
  --json-out domain-onboarding-report.json \
  --fail-on-blocked

PYTHONPATH=src python scripts/run_compounding_intelligence.py \
  --domain-manifest generalization/domain-packs/refinery-reference-v0.1.yaml \
  --onboarding-report domain-onboarding-report.json \
  --registry generalization/capabilities/registry-v0.1.yaml \
  --regression-suite generalization/regression/industrial-common-v0.1.yaml \
  --promotion-policy policies/capability-promotion-v0.1.yaml \
  --promotion-workflow workflows/capability-promotion-v0.1.yaml \
  --registry-out proposed-capability-registry.yaml \
  --json-out compounding-intelligence-report.json \
  --fail-on-blocked
```

For the Refinery reference canary, no promotion drafts are expected and the successful automated terminal state is `READY_FOR_RELEASE_REVIEW`. This does **not** mean the runner has released the domain; it means all automated evidence gates are satisfied and the next gate is human.

## GitHub Actions

After merge, use:

**Actions -> CEPIO Domain Onboarding -> Run workflow**

The normal input is the Domain Onboarding manifest. Optional inputs accept repository-relative, source-controlled promotion candidate, human promotion decision and release-decision artifacts.

The action uploads:

- `domain-onboarding-report.json`;
- `compounding-intelligence-report.json`;
- `proposed-capability-registry.yaml`.

The proposed registry is evidence output. Automation does not overwrite the committed versioned registry on `main`.

## v0.1 boundary

This slice establishes the governed compounding control plane. Human decisions are source-controlled review artifacts; they are not yet identity-bound to Entra/Kinetic authority records. A later management-plane slice can bind the same decision contracts to authenticated CEPIO Authority without changing the evidence, promotion or customer-isolation model.
