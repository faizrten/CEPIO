# Industry IQ Trusted Catalogue v0.6

CEPIO v0.6 adds a host-controlled catalogue and provenance boundary around the v0.5 Industry IQ pack registry.

The catalogue is **not** a marketplace, remote-code loader, or agent tool. It does not fetch arbitrary URLs, import agent-selected packages, install dependencies from the network, or treat a self-declared checksum as proof of trust. Source adapters live outside the agent boundary and are responsible for obtaining and verifying pack artifacts before presenting candidates to CEPIO Core.

## Lifecycle

```text
host-controlled source adapter
        ↓
artifact retrieval / verification outside Core
        ↓
IndustryIQPackProvenance
        ↓
IndustryIQTrustPolicy
        ↓
trusted catalogue admission
        ↓
IndustryIQPackRegistry
        ↓
dependency + Core compatibility + collision resolution
        ↓
IndustryIQCatalogueDeployment
        ↓
Skill BOUND / READY preflight
        ↓
READY-only dispatch
        ↓
invocation-time evidence
        ↓
governed Decision / Action
```

## Provenance contract

`IndustryIQPackProvenance` records:

- `source_id`: host identity for the configured source adapter;
- `source_kind`: builtin, repository, package, filesystem, or other;
- `source_ref`: immutable or otherwise meaningful source reference supplied by the host;
- `publisher`: optional publisher identity;
- `artifact_digest`: verified `sha256:<64 hex>` digest when required;
- `verification`: `builtin`, `host_verified`, or `unverified`.

`host_verified` is deliberately a host assertion. CEPIO Core does not claim to have downloaded or cryptographically verified a remote artifact merely because a digest string is present.

## Trust policy

`IndustryIQTrustPolicy` provides a small fail-closed admission policy:

- source IDs must be explicitly trusted;
- `unverified` provenance is rejected;
- builtin verification may only be used by builtin sources;
- when a publisher allowlist is configured, the candidate publisher must be present in it;
- external sources require a valid SHA-256 digest by default.

Trust admission is separate from dependency resolution. A pack may be trusted yet still fail registry resolution because of Core-version incompatibility, dependency conflicts, cycles, or capability collisions.

## Atomic source admission

One source discovery batch is admitted atomically. CEPIO stages every candidate, validates provenance and identity, and checks duplicate/conflicting records before mutating the catalogue. If one candidate fails, none of the candidates from that discovery call are admitted.

This prevents a partially trusted catalogue from being created when a repository or package index contains a malformed or untrusted entry.

## Identity and provenance conflicts

The key is `(pack_id, version)`.

- Re-presenting the identical trusted record fails as `CATALOGUE_PACK_ALREADY_PRESENT` rather than silently replacing it.
- Presenting the same pack/version with different provenance fails as `CATALOGUE_PACK_PROVENANCE_CONFLICT`.
- A source adapter cannot claim provenance for a different source ID; this fails as `CATALOGUE_SOURCE_MISMATCH`.

A later signing/attestation layer can strengthen artifact identity without changing this catalogue key or the v0.5 dependency resolver.

## Deployment evidence

`IndustryIQCatalogue.install()` delegates dependency and capability resolution to the existing `IndustryIQPackRegistry`. On success it returns `IndustryIQCatalogueDeployment`, containing:

1. the existing deterministic `IndustryIQDeploymentManifest`; and
2. trusted provenance for every selected pack.

The result is also attached to the runtime as `industry_iq_catalogue_deployment` for host-side deployment evidence. Skill preflight continues to consume the installed pack ID/version map; v0.5.1 version compatibility is unchanged.

## Security boundary

The intended authority model is:

```text
Agent / Skill
  may request a declared capability
  may NOT discover arbitrary sources
  may NOT alter trust policy
  may NOT install or upgrade packs
  may NOT bypass provenance admission

Host / deployment plane
  configures sources
  verifies artifacts
  configures trust policy
  admits catalogue candidates
  resolves and installs packs
  records deployment provenance
```

This preserves CEPIO's existing separation between reasoning and deployment authority.

## Next evolution

v0.6 intentionally stops before cryptographic signing infrastructure or remote package transport. Candidate follow-ons are:

- signed publisher attestations / Sigstore-style verification;
- SBOM and vulnerability-policy evidence bound to the artifact digest;
- repository/package source adapters implemented outside Core;
- tenant-specific catalogue policy overlays;
- promotion states such as LABS → QUALIFIED → RELEASED without weakening the immutable pack identity.

Any future remote discovery must remain host-controlled and must not expose package installation as an Operator or agent tool.
