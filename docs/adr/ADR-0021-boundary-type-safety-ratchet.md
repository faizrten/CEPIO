# ADR-0021 — Boundary Type-Safety Ratchet

**Status:** Proposed

## Context

CEPIO increasingly relies on narrow boundary modules for canonical runtime models, governed adapters, provider-neutral platform bindings, and source/domain binding contracts. These boundaries benefit from stricter static typing because type ambiguity at an integration boundary can become runtime contract ambiguity.

The repository already runs mypy as part of the Quality Gate, but its baseline remains intentionally incremental rather than repository-wide strict mode. A previous attempt to enable `disallow_any_generics` for `cepio.domain_bindings` required changing existing Pydantic field annotations. The public-compatibility gate correctly rejected that implementation because a static-analysis improvement must not silently alter an accepted Python interface.

`pyproject.toml` is a protected governance path. Any change to the type-checking policy therefore requires explicit architectural rationale and must pass the full governance-protection, compatibility, Quality Gate, CI, and CodeQL controls.

## Decision

Adopt a module-scoped type-safety ratchet:

- `cepio.adapters`, `cepio.model`, and `cepio.platform_bindings` enable `disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_any_generics`, `no_implicit_optional`, and `warn_return_any`.
- `cepio.domain_bindings` enables the same function/return/optional checks but deliberately defers `disallow_any_generics` so the existing public Pydantic contract remains unchanged.
- Do not enable repository-wide `strict = true` in this increment.
- Preserve all pre-existing packaging and runtime entry points while changing static-analysis configuration, including the `cepio-management = "cepio.management_api:main"` console script established by the Management Control Plane work.
- Do not weaken compatibility, coverage, security, architecture, governance, or CodeQL gates to make stricter typing pass.

## Rationale

The ratchet targets boundary-heavy modules where stronger typing most directly reduces integration defects, while preserving CEPIO's existing compatibility contract. Deferring one rule for `cepio.domain_bindings` is preferable to changing public annotations solely to satisfy a static checker. A future migration may tighten that module further when there is an independently justified contract version change.

Static-analysis changes must also be semantically narrow in packaging configuration. During promotion of this ADR, the existing `cepio-management` console entry point was unintentionally omitted from `pyproject.toml`; that deletion was outside the decision scope and is explicitly corrected. Future protected-configuration promotions must compare unrelated packaging surfaces as well as Python/API compatibility before merge.

## Consequences

### Positive

- New and modified boundary code is harder to leave partially typed.
- Generic-container ambiguity is reduced where it can be done without interface change.
- Provider and runtime implementations receive earlier static feedback.
- The compatibility gate remains authoritative over public-interface evolution.
- The Management Control Plane console entry point remains part of the packaged CEPIO runtime.

### Trade-offs

- `cepio.domain_bindings` does not yet receive `disallow_any_generics`.
- Type strictness remains intentionally non-uniform while legacy modules are ratcheted incrementally.

## Validation

This decision is accepted only when:

- the public and persisted compatibility checks report no contract change;
- mypy passes under the committed module-scoped configuration;
- repository CI and architecture/security tests remain green;
- changed-line and repository coverage gates remain satisfied;
- Governance and governance-protection checks pass;
- CodeQL reports no new alerts;
- the installed package still exposes the `cepio-management` console entry point and its existing Management API smoke tests remain green.

No runtime semantics, serialized field names, ontology concepts, public API operations, policy authority, or customer-specific behavior are changed by the type-safety decision itself.
