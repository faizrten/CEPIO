# ADR-006: Enterprise Knowledge Sovereignty and User Context Boundary

Status: Accepted

## Context

CEPIO needs to serve multiple industrial enterprises and multiple personas inside each enterprise without becoming a multi-tenant knowledge-sharing mechanism or a user-specific source of truth. The operating ontology must remain reusable while proprietary operating knowledge stays with the enterprise that generated it.

## Decision

CEPIO adopts four architectural invariants:

1. **Enterprise truth is enterprise-owned.** Operational state, source mappings, policies, decision functions, workflows, historical decisions, learned models and evidence remain inside the enterprise boundary that generated them.
2. **Canonical CEPIO semantics contain no customer intellectual property.** Customer-specific terms begin at PROFILE scope. Promotion to DOMAIN or CORE is allowed only for the reusable abstraction, never for customer data, thresholds, algorithms, rules, procedures or learned behavior.
3. **User context changes view and authority, not truth.** Identity, role, scope and authority may filter what a user or agent can see or do. They must not create contradictory enterprise facts.
4. **Cross-enterprise learning promotes abstractions only.** The Generalization Lab may use repeated requirements across customers/archetypes as evidence for a reusable semantic abstraction. It must not promote enterprise-specific operating logic into shared CEPIO modules.

## Scope boundary

This ADR is a constraint, not a new platform subsystem. CEPIO will not implement a dedicated tenancy platform, user-preference service, vector-memory layer, encryption service or SaaS control plane solely to satisfy this decision.

Existing platform capabilities should carry those concerns where appropriate:

- Entra or equivalent identity provider for identity and role claims;
- deployment/runtime isolation for enterprise data boundaries;
- customer/platform storage for enterprise state and memory;
- CEPIO policy and authority semantics for governed access and action.

## Semantic promotion rule

A new requirement discovered in one enterprise starts as `PROFILE` unless it is already supported by an existing shared abstraction.

Promotion path:

`PROFILE -> DOMAIN -> CORE`

Promotion requires independent evidence that the abstraction recurs across materially different operating contexts. Only the abstraction may move upward. Enterprise data, rules, thresholds, decision logic and models never move with it.

## User-context rule

A persona-specific experience is a projection over the same enterprise state:

`enterprise truth + identity + role + scope + authority + current task -> contextual view/action surface`

CEPIO therefore does not maintain persona-specific versions of enterprise truth.

## Consequences

- The Operator Agent must use actor identity/roles and CEPIO policy, but cannot maintain a private enterprise truth store.
- REST/MCP interfaces must preserve the same authorization and evidence boundaries.
- Generalization tests must distinguish reusable semantic pressure from enterprise-specific operating logic.
- Future multi-tenant/SaaS work may implement stronger isolation, but it is not a prerequisite for validating CEPIO's operating abstraction.
