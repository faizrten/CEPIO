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
