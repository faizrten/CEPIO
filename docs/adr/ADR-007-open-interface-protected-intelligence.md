# ADR-007: Open Interface, Protected Intelligence

Status: Accepted

## Context

CEPIO benefits from being developed in public because public specifications, interfaces, examples and reference components improve interoperability, validation, trust and ecosystem adoption. At the same time, publishing every implementation detail, domain intelligence asset, benchmark corpus or reasoning method would unnecessarily reduce CEPIO's commercial defensibility.

Public visibility and open-source licensing are separate decisions. CEPIO therefore needs an explicit architectural publication boundary independent of repository visibility.

## Decision

CEPIO adopts an **open-interface / protected-intelligence** architecture.

1. **Public interfaces are first-class product surfaces.** Stable REST, MCP and SDK contracts, conceptual architecture, interoperability specifications, selected semantic abstractions and sanitized examples may be developed publicly when doing so improves adoption and ecosystem value.
2. **Differentiated intelligence need not be public to be interoperable.** Generalization methods, benchmark corpora, proprietary industrial reasoning, advanced competency packs, semantic-promotion heuristics, decision/action logic and other differentiating implementations may remain protected behind published contracts.
3. **Customer-confidential information is a separate ownership zone.** Customer data, mappings, thresholds, procedures, policies, models, learned behaviour and customer-specific operating logic must not be promoted into public CEPIO merely because CEPIO can represent them.
4. **Publication is an explicit decision.** New work that may constitute differentiated CEPIO know-how should default to a protected workspace until an intentional public artifact is selected.
5. **The narrowest useful public artifact is preferred.** Where an API contract, ontology abstraction, sanitized example or reference scenario provides the necessary ecosystem value, CEPIO should not publish deeper implementation solely for symmetry with the interface.

## Working boundaries

CEPIO uses three publication classes:

- `PUBLIC` — deliberately public and intended to evolve in `faizrten/CEPIO`;
- `PROTECTED` — developed privately; only approved abstractions/interfaces/examples are published;
- `CUSTOMER CONFIDENTIAL` — retained in the appropriate customer-controlled boundary and prohibited from the public repository.

The detailed engineering publication policy is maintained in `docs/governance/ip-publication-policy.md`.

## Relationship to ADR-006

ADR-006 governs **knowledge sovereignty**: enterprise truth remains enterprise-owned and reusable abstractions may be generalized without carrying customer IP upward.

ADR-007 governs **publication exposure**: even reusable CEPIO-owned abstractions or implementation methods may remain protected when public disclosure is not required for interoperability or adoption.

The two controls are complementary:

```text
customer truth / customer IP
        -> governed by ADR-006

CEPIO-owned reusable capability
        -> governed by ADR-007 publication classification
```

## Consequences

- public CEPIO remains useful, inspectable and integration-friendly;
- private CEPIO Labs may contain differentiated implementation without changing public interface contracts;
- pull requests to the public repository require an IP/publication classification;
- Generalization Lab outputs may have both a protected implementation artifact and a deliberately narrower public artifact;
- a public ontology or API surface does not imply that all supporting evaluation, reasoning or runtime intelligence is public;
- existing public material is treated as disclosed; future evolution can move behind protected boundaries without assuming deletion reverses prior publication.

## Non-goals

This ADR does not determine software licensing, patentability, trademark ownership, employment-IP rights, contributor agreements or customer contractual rights. Those questions require separate legal and commercial review where material.
