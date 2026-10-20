# Industry IQ Supply-Chain Trust v0.6.1

## Purpose

v0.6 established a host-controlled trusted catalogue for Industry IQ packs. v0.6.1 strengthens that boundary with optional production-grade supply-chain evidence that is cryptographically verified by the host or source adapter and then enforced by CEPIO Core.

The governing invariant is:

> A pack version is not trusted merely because its metadata names a publisher or contains a checksum. Supply-chain evidence must refer to the exact admitted artifact digest, and the host must verify any signature or security evidence before Core accepts it.

## Architecture

```text
external pack artifact
        |
        +--> host verifies publisher signature / attestation
        |
        +--> host verifies SBOM evidence
        |
        +--> host verifies vulnerability scan evidence
        |
        v
IndustryIQPackProvenance
        |
        v
IndustryIQSupplyChainPolicy
        |
        +--> publisher identity / signer / predicate policy
        +--> artifact digest binding
        +--> SBOM format + document digest policy
        +--> vulnerability severity + SBOM binding policy
        |
        v
trusted catalogue admission
        |
        v
Industry IQ registry resolution / installation
        |
        v
provenance-bearing deployment evidence
        |
        v
Skill compatibility + READY preflight
```

## Host verification boundary

CEPIO Core does **not**:

- fetch signatures from the network;
- hold signing private keys;
- verify Sigstore, X.509, PGP, GitHub, Azure, or package-registry signatures directly;
- fetch or generate an SBOM;
- invoke a vulnerability scanner;
- trust a self-declared signature merely because a signature reference exists.

Those are deployment/source-adapter responsibilities.

Core receives the verification result and deterministically enforces identity and digest binding. This keeps network access, cryptographic implementation, package retrieval, and scanner selection outside the agent/runtime trust boundary.

## Evidence contracts

### Signed publisher attestation

`IndustryIQPublisherAttestation` records:

- artifact subject digest;
- publisher identity;
- signer identity;
- signature kind (`sigstore`, `x509`, `pgp`, or `other`);
- external signature/attestation reference;
- attestation predicate type;
- host verification status.

When present, the attestation must be host-verified and its subject digest must exactly match the pack artifact digest. Its publisher must match the catalogue provenance publisher. Trust policy may also allow-list signer identities and attestation predicate types.

### SBOM evidence

`IndustryIQSBOMEvidence` records:

- artifact subject digest;
- SBOM document digest;
- SBOM format (`spdx`, `cyclonedx`, or `other`);
- external evidence reference;
- host verification status.

The SBOM subject digest must match the admitted artifact digest. Trust policy may restrict accepted SBOM formats. Both the subject and document identities use SHA-256 content identity.

### Vulnerability evidence

`IndustryIQVulnerabilityScan` records:

- artifact subject digest;
- optional SBOM document digest;
- scanner identity/version;
- evidence reference;
- highest observed severity;
- host verification status.

The scan must refer to the same artifact digest. If an SBOM is admitted, the scan must also bind to that exact SBOM document digest. Trust policy may set the maximum accepted vulnerability severity. `unknown` is treated as more severe than `critical` for fail-closed threshold comparison.

## Strict external-pack mode

v0.6.1 is backward compatible: the default `IndustryIQSupplyChainPolicy` does not retroactively require new evidence for hosts already using the v0.6 catalogue.

For separately distributed or remotely sourced Industry IQ packs, use:

```python
IndustryIQSupplyChainPolicy.strict_external(...)
```

Strict mode requires all three:

1. signed publisher attestation;
2. SBOM evidence;
3. vulnerability scan evidence.

It can additionally require:

- trusted signer identities;
- approved attestation predicate types;
- approved SBOM formats;
- a maximum vulnerability severity.

Future remote source adapters should qualify through strict mode rather than weakening catalogue admission.

## Fail-closed conditions

Admission fails before registry/runtime mutation for conditions including:

- missing required publisher attestation;
- unverified publisher attestation;
- invalid or mismatched attestation subject digest;
- publisher identity mismatch;
- untrusted signer;
- disallowed attestation predicate;
- missing or unverified SBOM;
- invalid/mismatched SBOM artifact or document digest;
- disallowed SBOM format;
- missing or unverified vulnerability scan;
- scan artifact digest mismatch;
- scan-to-SBOM digest mismatch;
- vulnerability severity exceeding policy.

The catalogue preserves its v0.6 atomic-ingestion invariant: a rejected candidate cannot be partially admitted.

## Security and IP boundary

Supply-chain evidence proves artifact identity and deployment trust. It does not make pack contents public and does not change CEPIO's IP classification model.

A public catalogue can expose safe package metadata, versions, publisher identity, and non-sensitive artifact provenance while protected procedures, customer mappings, eval corpora, thresholds, and differentiated Industry IQ content remain outside public metadata.

## Relationship to compiled Industry IQ

Compiled Industry IQ is a runtime acceleration projection. Supply-chain trust is a deployment admission concern.

```text
trusted artifact admission                  runtime acceleration
--------------------------                  --------------------
signature / SBOM / scan                     Capability Registry
        |                                           |
        v                                           v
Industry IQ catalogue                      Compiled Capability Bundle
        |                                           |
        +--------------- governed IQ ---------------+
```

The cache never substitutes for catalogue trust, and catalogue trust never substitutes for runtime Skill/evidence/authority checks.

## Next boundary

v0.7 can add concrete repository/package source adapters (for example GitHub release/package or Azure/private registry adapters) that retrieve artifacts and produce these host-verified evidence contracts. Those adapters remain outside Skills and Operators and must not grant autonomous install or upgrade authority to agents.
