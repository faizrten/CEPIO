# CEPIO IP and Publication Policy

## Purpose

CEPIO is developed in public where openness improves adoption, interoperability, trust and ecosystem participation. Public development must not unnecessarily disclose differentiated implementation, proprietary industry intelligence or customer-confidential information.

This policy establishes the publication boundary for CEPIO work.

## Classification model

Every material change should be classified before publication.

### PUBLIC

Use for artifacts whose publication creates more ecosystem value than replication risk.

Typical examples:

- North Star and conceptual architecture;
- public API, MCP and SDK contracts;
- interoperability specifications;
- selected canonical semantic abstractions;
- standards alignment and mapping guidance;
- sanitized examples and reference scenarios;
- deliberately public reference implementations;
- public roadmap and release documentation.

### PROTECTED

Use for work that materially contributes to CEPIO's differentiated implementation, proprietary know-how or commercial defensibility.

Typical examples:

- Generalization Lab benchmark corpora, scoring and evaluation assets;
- semantic-promotion heuristics and internal normalization methods;
- advanced industrial competency packs;
- industrial reasoning, decision and action logic;
- proprietary function libraries and agentic execution patterns;
- cross-domain pattern intelligence;
- non-public evaluation datasets and failure taxonomies;
- implementation details that can instead be represented publicly through a stable interface.

Protected work should be developed in the private `faizrten/CEPIO-Labs` repository unless a more restrictive boundary is required.

### CUSTOMER CONFIDENTIAL

Use for customer-derived or customer-owned information.

Typical examples:

- customer source mappings;
- enterprise operating data or state;
- thresholds, procedures and policies;
- customer-specific models, algorithms or learned behaviour;
- customer decision logic;
- confidential architecture or integration details;
- material governed by NDA, contract or customer security policy.

Customer-confidential material must remain in the appropriate customer-controlled boundary. It must not be placed in the public CEPIO repository and should not be placed in CEPIO-Labs unless the relevant agreement and access controls explicitly allow it.

## Publication principle

CEPIO follows an **open-interface / protected-intelligence** model.

The preferred publication path is:

```text
PROTECTED implementation
        -> IP review
        -> public abstraction / interface / sanitized example
        -> faizrten/CEPIO
```

A public interface does not require the corresponding implementation, benchmark corpus, industrial reasoning method or domain intelligence to be public.

## Decision test

Before publishing a material change, ask:

1. Does publication materially improve adoption, interoperability, validation or trust?
2. Would the artifact materially help a third party reproduce CEPIO's differentiated capability?
3. Can the same ecosystem value be achieved by publishing an interface, abstraction, specification or sanitized example instead?
4. Does the change contain customer-derived information or third-party confidential material?
5. Could publication affect a future patent, trade-secret or commercialization decision?

When classification is uncertain, default to **PROTECTED** and make an explicit publication decision later.

## Ownership zones

CEPIO distinguishes three ownership zones:

1. **Public CEPIO** — deliberately published specifications, interfaces, SDKs, selected semantics, examples and reference components.
2. **CEPIO proprietary intelligence** — protected methods, industry intelligence and differentiated implementation.
3. **Customer proprietary intelligence** — customer data, mappings, rules, procedures, policies, thresholds, models and enterprise-specific knowledge.

The existing CEPIO semantic promotion principle remains separate from publication classification. A semantic abstraction may be promoted from PROFILE to DOMAIN or CORE only when it is genuinely reusable; customer data, rules, thresholds, procedures and learned behaviour do not move with it.

## Pull-request requirement

Every material public PR must declare one classification:

- `PUBLIC`
- `PROTECTED — public abstraction only`
- `CUSTOMER CONFIDENTIAL — publication prohibited`

A PR classified as `PROTECTED — public abstraction only` must explain what remains private and why the proposed public surface is safe to publish.

A PR containing customer-confidential material must not be merged into the public repository.

## Existing public material

Material already committed to the public repository should be treated as previously disclosed. Removing it from the current tree does not reliably reverse publication because Git history, forks, clones and caches may exist.

The practical objective is therefore:

- establish the current repository as the public baseline;
- prevent unnecessary future disclosure;
- stop publicly evolving components that should become protected;
- publish future interfaces or abstractions from protected implementations where appropriate.

## Legal boundary

This document is an engineering and publication-control policy, not a software license, patent opinion or legal determination of ownership. Licensing, trademark, patentability, employment-IP and contributor-rights decisions should be reviewed separately with qualified counsel where material.

## 2026-10-22 founder IP containment override

The previously open-source-style full-stack repository carries material implementation and qualification assets, not just developer interfaces. It must be treated as a **proprietary source repository** during the transition to a deliberately extracted public developer surface.

Until repository visibility has been changed to private, the required `governance-protection` check embargoes new or modified runtime, data, evaluation, automation, ontology, profile and industrial-competency assets. Pure removals remain allowed. This is a publication freeze, not a substitute for changing visibility.

After the repository becomes private, internal implementation work may resume through the normal protected-branch and governance checks. Anything subsequently published must be deliberately extracted into a separately managed public developer repository following the Labs IP register and publication-candidate review. No bulk mirroring of private source trees into public repositories is permitted.

A public baseline, including Git history and third-party clones, cannot be made secret retroactively. Perform a customer-confidentiality and credential-exposure audit, rotate any exposed secrets, and review IP ownership/licensing before subsequent disclosure. This policy does not purport to create retroactive confidentiality or to determine legal rights.


## 2026-10-22 final repository architecture — open CEPIO, protected Industry IQ

**Supersedes the earlier 2026-10-22 proposal to make the entire CEPIO repository private.** The founder elects to keep `faizrten/CEPIO` PUBLIC as an interoperability/runtime platform and evolve differentiated industrial competence in PRIVATE `faizrten/CEPIO-Labs`. The former blanket public-code embargo is withdrawn in favor of classification-aware public code review and protected-path enforcement.

**Public CEPIO:** canonical reusable ontology, identity/time/state/provenance, generic policy and governed actions, public Capability/Performance/Skill contract schemas, REST/MCP/SDK, interoperable bindings, documentation and deliberately sanitized examples. Ordinary public platform development may continue with successful mandatory CI, governance and publication attestations.

**Private Industry IQ:** domain-specific industrial algorithms, sophisticated agent planning, differentiated expert Skills, advanced evaluation and grading, detailed persona/competency packs, normalization, learning and industry-performance heuristics. New development begins privately by default. No direct public-to-private source/runtime dependency is permitted: the public CEPIO package must build and function on its own. Private code may use stable public interfaces; private deployments can compose the two through governed contracts.

**Customer-confidential:** customer mappings/profiles and operating rules require their own enterprise-controlled boundary, not public CEPIO and not shared Labs by default. Existing `profiles/satorp/` is a review priority; historical public disclosure does not establish permission for future customer publication.

**Migration discipline:** copying an already-public historical artifact into Labs does not restore secrecy. Preserve release and test compatibility; do not remove current public runtime modules or CI-dependent baselines until private equivalents pass release qualification. Only intentionally extracted contracts/SDKs/sanitized sample artifacts may move outward.

**Publication automation:** the required `governance-protection` check denies additions/modifications/renames into categorized proprietary paths and customer-profile trees, yet permits deletions after migration. For other public code changes it requires one IP classification plus four explicit publication attestations. As with all path checks, this is a guardrail, not proof that every new path is safe: human review of IP, confidential contents and third-party rights remains mandatory.

**Deployment invariant:** Azure, REST/MCP, Industry IQ Studio and Foundry clients retain their published interfaces. Any future private packaging or integration must undergo contract, authorization and performance regression testing, with no customer data or protected private code exposed in public CI artifacts.
