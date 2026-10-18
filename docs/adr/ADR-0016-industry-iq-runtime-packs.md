# ADR-0016: Industry IQ runtime packs

## Status

Accepted for v0.4 qualification.

## Context

The CEPIO north star is **thin infrastructure, thick industrial intelligence**. Core must remain small and stable while domain-specific semantics, procedures, risk/failure patterns, decision patterns, constraints, KPI/economic logic and workflows live in Industry IQ packs.

The `investigate-drilling-npt` Skill is the first strong generalization test of that boundary. Its remaining capability gaps are domain-specific: NPT duration derivation, a drilling NPT follow-up Decision and an NPT investigation Action. Adding these permanently to generic Core registries would make Core grow with every Skill and contradict the north star.

The existing drilling ontology already provides precise domain semantics (`OperatingRig`, `ActivityInterval`, `DrillingActivityClassification`, `RigOperationalEvent`) and the OSDU/ADME binding contract treats Wellbore as reusable external context rather than a CEPIO-owned canonical object.

## Decision

1. Add a minimal `IndustryIQPack` runtime extension contract to CEPIO Core.
2. `build_runtime()` remains domain-light and API-compatible; callers install Industry IQ packs explicitly after runtime creation.
3. A pack may register domain-specific Functions, Decisions and Actions through the existing governed runtime APIs. It does not bypass policy, preflight, Action Runtime, evidence, audit or Decision validation.
4. The drilling NPT pack registers:
   - `calculateNPTDuration`;
   - `npt-follow-up-recommendation`;
   - `CreateNPTInvestigation`.
5. The drilling ontology remains the owner of drilling semantics. v0.4 adds only the source-neutral `NPTInvestigation`, `investigatesActivity`, and normalized `isProductive` meaning required for NPT reasoning.
6. NPT remains a **derived interpretation**, not a canonical NPT event class. External IADC/WITSML codes remain federated/source-owned.
7. Wellbore remains OSDU/ADME `REUSE` context. A Skill must not force a CEPIO Wellbore class into Core merely to become BOUND.
8. User experience remains headless. Copilot, CEPIO Workspace, agents and other clients consume the same governed Skill/runtime surface through APIs/MCP/SDK; drilling business logic does not move into UI code.

## Governance and authority

Industry IQ installation is explicit and visible to Skill preflight. A Skill that declares a required pack is BLOCKED when the pack is absent. The drilling Skill identity is recommendation-only; direct execution remains separately governed for human drilling roles. Existing policy, Decision-to-Action causality and audit gates remain enforced.

## Validation

The v0.4 qualification proves:

- Core has no drilling NPT function, Decision or Action before explicit pack installation.
- Pack installation exposes only the declared drilling capabilities and duplicate installation fails closed.
- Missing required pack blocks before trigger matching or Operator construction.
- NPT duration is derived only from governed rig/well/activity links, timezone-aware interval evidence and normalized productivity classification.
- Missing, contradictory or malformed evidence fails closed rather than being guessed.
- `npt-follow-up-recommendation` is ActivityInterval-scoped.
- The recommendation identity cannot execute `CreateNPTInvestigation`; human drilling roles remain the execution boundary.
- Decision-to-Action `decision_id` audit causality is preserved.
- Existing compatibility, architecture, security, drilling, coverage and governance gates remain green.

## Consequences

The same CEPIO Core can run with zero, one or many Industry IQ packs. Deployment-specific domain capability can evolve without turning every industrial function into permanent Core infrastructure.

This architecture remains Microsoft-native without becoming Microsoft-dependent: Fabric, OSDU/ADME, SAP and PI are replaceable authoritative bindings, while Copilot is an experience surface rather than the owner of industrial semantics.

## Rejected alternatives

### Add generic `Rig`, `DrillingActivity`, or `OperationalEvent` aliases to Core

Rejected. Existing drilling types are more precise and already source-neutral.

### Add CEPIO `Wellbore` purely to satisfy the Skill

Rejected. Wellbore remains authoritative OSDU/ADME reusable context.

### Put `calculateNPTDuration` in generic `cepio.functions`

Rejected. NPT calculation is drilling Industry IQ, not universal Core infrastructure.

### Model NPT as a canonical event type

Rejected. NPT is derived from activity/productivity classification plus causal downtime/failure evidence; source reporting taxonomies remain external and provenance-preserved.
