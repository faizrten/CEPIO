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

## Intelligence Sovereignty Contract — boundary for global compounding

The adopted product principle is **collective industrial progress with sovereign enterprise intelligence**. The registry records reusable, qualified *capability*, not aggregated ownership of customer operational memory. Existing PROFILE/customer isolation remains mandatory.

Each globally considered capability evidence reference should carry, or resolve to, a reviewed provenance/rights declaration: original source and owner, tenant scope, source class, permitted uses (including whether shared evaluation or global learning is allowed), derivation lineage, version/hash, reviewer identity and expiry/retention. A missing or expired global-learning permission is a rejection—not a reason to infer permission from use at runtime.

There are three provenance domains: (a) CEPIO-owned or lawfully licensed/reusable industrial knowledge, (b) customer-controlled operational intelligence, and (c) separately permissioned contributions after IP, confidentiality and leakage review. Customer-specific learned behavior, model adaptations, embeddings, prompts, telemetry and synthetic derivatives are not promoted globally by default. Independently authored or authorized Labs synthetic scenarios can improve general qualification **without** relying on customer records. Re-identification and trade-secret exposure risks remain even when data is called synthetic or anonymized.

For a future production-qualified implementation, require fail-closed tests for cross-tenant retrieval, unauthorized training/evaluation reuse, mixed-tenant indices/caches, evaluator answer leakage, log/export disclosure, approval forgery and unauthorized action. The current v0.1 registry has narrower source/path rejection and human review controls; these new requirements are **target qualification criteria**, not claims of tests already passing.

Capability promotion remains independent of scenario generation, deployment, customer-specific inference and release. No increase in maturity or score is earned for documenting this policy alone.

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
