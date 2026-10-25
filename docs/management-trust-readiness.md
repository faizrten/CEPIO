# Management trust and readiness — staged implementation

## Scope and claim boundary

This change preserves CEPIO Management as a read-only control-plane projection over the same Core runtime as REST and MCP. The API does not run Skills, launch investigations, approve decisions, probe customer endpoints on request, or release raw customer evidence.

- `/management/v1/health` is **process liveness only**, not proof of databases, SAP/PI, Foundry or model connectivity. Hosted response is marked `local_only=false`; local launcher remains loopback-only.
- `/management/v1/capabilities` reports actual in-process Function, Decision and Action registrations plus the inventory origin for shipped Skill descriptors. `readiness_qualified=false` does not imply any Skill is ready for a specific actor, target or evidence set.
- `/management/v1/bindings` preserves registration `status` for compatibility and **separately** reports `verified_readiness`. A `ready` registration alone never produces `verified`. Only server-supplied, evidence-referenced, unexpired checks are accepted; stale, failed and unverified states are explicit. No automated customer-network probe is launched.
- `/management/v1/industry-iq` continues to report runtime-installed versions; exact-version matching deployment manifests add Core constraints and declared capability composition where available. Available source catalog entries are not installed packs.
- `/management/v1/investigations` is a read-only, aggregate-only **contract**. In the absence of a trusted tenant-scoped observer, `state=not-connected`, `counts=null`. An observer is called with verified actor tenant ID and the tenant ID on its result must match. Synthetic Labs Rig 07 decisions are not represented as Core production runs.

## Deliberately remaining gaps

1. **Live binding registry wiring:** The current hosted Core bootstrap does not supply actual Binding Contract registrations. Management reports `binding_inventory_state=not-wired` rather than implying an empty inventory proves there are no bindings. Host integration must provide canonical registrations and trusted probe evidence before verified-ready counts are possible.
2. **Actor-aware Skill readiness:** Shipped Skill descriptors are not execution preflight. Per actor/subject readiness still requires the governed Application Contract and evidence.
3. **Qualified deployments:** Versioned pack deployment manifests record code composition, not external field qualification or authorization.
4. **Live investigation telemetry:** Management intentionally has no direct CEPIO Labs dependency. After a canonical Core investigation/workflow observer with tenant scoping exists, it may provide summary counts to this contract; until then, the unavailable state must remain visible.
5. **Live operational proof:** CI/unit tests exercise fail-closed contracts, but do not attest any external customer integration, multi-tenant enterprise certification or production SLO.

## Tests and release gates

- Regression: local and remote Management routes are GET-only; non-reader and anonymous requests fail closed.
- New: registration without verification is `not-verified`; only valid current probe evidence can be `verified`. Expired, failed and future checks cannot be interpreted as readiness.
- New: pack manifest data applies only to exact runtime-installed version.
- New: no synthetic investigation counts are invented; mismatched tenant observer responses return degraded without counts.
- New: process-only health scope and authenticated remote metadata.
- Generated Management OpenAPI snapshot reviewed with additive response descriptors and `/investigations` endpoint. Run the repository's OpenAPI compatibility workflow against the base before merge.

## Rollout

Deploy CEPIO Core first, then Studio's separate compatibility PR. Do not attach a customer-data observer or activate probe collection without tenant-specific authorization and operational review. No new resource, paid inference, or role grants are introduced.
