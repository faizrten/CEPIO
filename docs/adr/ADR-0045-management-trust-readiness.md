# ADR-0045: Truthful Management readiness and tenant-scoped investigation observation

- Status: Proposed
- Date: 2026-10-25
- Scope: Public CEPIO Management Contract only

## Context

The v0.1 Management Contract reports installed pack IDs/versions, shipped Skill specifications and static binding registrations, but none of these prove actor-specific Skill readiness or a working external customer connection. The process-level health descriptor formerly implied more than it tested. The hosted Management projection is remotely authenticated while the shared model described loopback access.

Industry IQ Studio must not mistake absent registrations for definitive absence of integrations, or synthetic CEPIO Labs Rig 07 evidence for an active customer investigation.

## Decision

1. Keep Application REST/MCP and Management as separate contracts over the *same* CEPIO runtime. Do not add a microservice or change authority to issue industrial Actions.
2. Define Health as process-only, distinguishing local loopback and authenticated remote access in the appropriate projection.
3. Report actual in-process Function/Decision/Action registration counts. Label Skill metadata as shipped specifications and require runtime actor-aware preflight for a readiness claim.
4. Preserve registered binding status for compatibility; add independent `verified_readiness` constrained to an explicit server-supplied check with bounded freshness and evidence reference. No external probes are executed by Management GET endpoints.
5. Show precise installed pack IDs/versions and only attach capability/dependency composition when a matching runtime deployment manifest exists.
6. Permit an additional read-only `/management/v1/investigations` aggregate projection. It returns unavailable/null by default, and future observations must be supplied by a trusted tenant-scoped server observer; observed tenant must equal authenticated Management actor tenant. No customer evidence, run details or approval authority are exposed.

## Security and governance

- [x] Existing gates remain enforced.
- Management remains GET-only, role gated and sanitized, including when hosted.
- The new aggregate endpoint fails closed with no observer, unknown tenant or mismatched observer scope.
- A general Management Reader role never grants access to raw customer investigation records or Labs protected evaluator material.
- No new credentials, role grants, infrastructure, paid inference, code execution or external data writes are introduced.
- Changes are additive at the public contract level and their complete OpenAPI snapshot is version-reviewed.

## Explicit limitations

Current CEPIO bootstrap does not register customer bindings into the hosted Management service. `binding_inventory_state=not-wired` is the correct live status until such wiring exists. Probe evidence is not synthesized. The active synthetic Rig 07 Labs workflow is a separate development/private boundary and is not a Core production investigation. The new aggregate endpoint will continue to show `not-connected` until trusted, tenant-scoped Core workflow telemetry is available.

## Validation

Unit tests require explicit, unexpired verification, reject future/failed/stale evidence, validate exact-version pack manifest provenance, check management process-only health and remote access, and prevent cross-tenant aggregate disclosure. Existing anonymous and non-reader security tests, GET-only checks, generated OpenAPI baseline and CI governance protections remain required.

## Consequences

The display may temporarily show more unavailable or unknown information; this is safer and more accurate than interpreting static declarations as operational readiness. The management plane stays thin and provider-neutral while future trusted adapters can populate verified evidence without rewriting the UI.
