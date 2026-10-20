from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Literal, Protocol
from urllib.parse import quote

import httpx
import jwt
from pydantic import BaseModel, Field

from .industry_iq import IndustryIQPack, industry_iq_manifest
from .industry_iq_catalogue import IndustryIQCatalogueCandidate, IndustryIQPackProvenance
from .industry_iq_supply_chain import (
    IndustryIQPublisherAttestation,
    IndustryIQSBOMEvidence,
    IndustryIQSupplyChainEvidence,
    IndustryIQVulnerabilityScan,
    SBOMFormat,
    VulnerabilitySeverity,
)

_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_API_BASE = "https://api.github.com"


class IndustryIQSourceAdapterError(ValueError):
    """Fail-closed remote source acquisition or verification failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IndustryIQGitHubReleaseDescriptor(BaseModel):
    """Declarative release descriptor for one Industry IQ pack artifact."""

    schema_version: Literal["cepio.industry-iq.release.v1"] = "cepio.industry-iq.release.v1"
    pack_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    artifact_asset_name: str = Field(min_length=1)
    artifact_digest: str = Field(min_length=1)
    evidence_asset_name: str = Field(min_length=1)
    sbom_asset_name: str = Field(min_length=1)


class IndustryIQGitHubReleaseConfig(BaseModel):
    """Pinned GitHub Release identity used by the repository source adapter."""

    repository: str = Field(min_length=3)
    release_tag: str = Field(min_length=1)
    descriptor_asset_name: str = "cepio-industry-iq.json"
    expected_release_id: int | None = None
    allow_prerelease: bool = False


class IndustryIQReleaseTransport(Protocol):
    """Network boundary used by the GitHub Release adapter."""

    def get_json(self, url: str) -> Mapping[str, object]: ...

    def get_bytes(self, url: str) -> bytes: ...


class HTTPXGitHubReleaseTransport:
    """Authenticated GitHub REST transport suitable for public or private releases."""

    def __init__(
        self,
        *,
        token: str | None = None,
        client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.Client(
            headers=headers,
            timeout=timeout_seconds,
            follow_redirects=True,
        )
        self._headers = headers

    def get_json(self, url: str) -> Mapping[str, object]:
        response = self._client.get(url, headers=self._headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise IndustryIQSourceAdapterError(
                "PACK_SOURCE_RESPONSE_INVALID",
                "GitHub Release API response must be a JSON object.",
            )
        return payload

    def get_bytes(self, url: str) -> bytes:
        headers = dict(self._headers)
        headers["Accept"] = "application/octet-stream"
        response = self._client.get(url, headers=headers)
        response.raise_for_status()
        return response.content


class IndustryIQPackResolver(Protocol):
    """Host-controlled resolver for already-approved executable pack implementations."""

    def resolve(self, pack_id: str, version: str) -> IndustryIQPack: ...


class StaticIndustryIQPackResolver:
    """Resolve remote artifact identities only to host-preinstalled pack implementations."""

    def __init__(self, packs: Iterable[IndustryIQPack]) -> None:
        self._packs: dict[tuple[str, str], IndustryIQPack] = {}
        for pack in packs:
            manifest = industry_iq_manifest(pack)
            key = (manifest.pack_id, manifest.version)
            if key in self._packs:
                raise IndustryIQSourceAdapterError(
                    "PACK_IMPLEMENTATION_DUPLICATE",
                    f"Duplicate host pack implementation: {manifest.pack_id}@{manifest.version}",
                )
            self._packs[key] = pack

    def resolve(self, pack_id: str, version: str) -> IndustryIQPack:
        try:
            return self._packs[(pack_id, version)]
        except KeyError as exc:
            raise IndustryIQSourceAdapterError(
                "PACK_IMPLEMENTATION_UNAVAILABLE",
                f"No host-approved Industry IQ implementation for {pack_id}@{version}.",
            ) from exc


class IndustryIQTrustedReleaseSigner(BaseModel):
    """Host trust root for cryptographic verification of one release evidence signer."""

    key_id: str = Field(min_length=1)
    signer_identity: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    public_key_pem: str = Field(min_length=1)
    algorithms: set[Literal["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]] = Field(
        default_factory=lambda: {"RS256", "ES256"}
    )


class IndustryIQSignedSBOMClaim(BaseModel):
    document_digest: str = Field(min_length=1)
    format: SBOMFormat


class IndustryIQSignedVulnerabilityClaim(BaseModel):
    scanner: str = Field(min_length=1)
    scanner_version: str | None = None
    highest_severity: VulnerabilitySeverity
    sbom_document_digest: str = Field(min_length=1)


class IndustryIQSignedReleaseEvidenceClaims(BaseModel):
    """Claims signed by the publisher release evidence JWS."""

    schema_version: Literal["cepio.industry-iq.evidence.v1"] = "cepio.industry-iq.evidence.v1"
    pack_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    subject_digest: str = Field(min_length=1)
    predicate_type: str = Field(min_length=1)
    sbom: IndustryIQSignedSBOMClaim
    vulnerability_scan: IndustryIQSignedVulnerabilityClaim


class IndustryIQReleaseEvidenceVerifier(Protocol):
    """Cryptographic verifier boundary used after artifact acquisition."""

    def verify(
        self,
        *,
        descriptor: IndustryIQGitHubReleaseDescriptor,
        artifact_digest: str,
        evidence_blob: bytes,
        evidence_source_ref: str,
        sbom_blob: bytes,
        sbom_source_ref: str,
    ) -> IndustryIQSupplyChainEvidence: ...


class JWSIndustryIQReleaseEvidenceVerifier:
    """Verify a compact JWS evidence bundle against host-controlled public keys.

    The unverified JWT header may select only a configured ``kid``. Publisher and signer
    identity come from the matching host trust root, never from an unverified payload.
    The signed claims bind pack identity, artifact digest, SBOM digest, and vulnerability
    result into one cryptographically verified release statement.
    """

    def __init__(self, signers: Iterable[IndustryIQTrustedReleaseSigner]) -> None:
        self._signers: dict[str, IndustryIQTrustedReleaseSigner] = {}
        for signer in signers:
            if signer.key_id in self._signers:
                raise IndustryIQSourceAdapterError(
                    "PACK_EVIDENCE_SIGNER_DUPLICATE",
                    f"Duplicate Industry IQ evidence signer key ID: {signer.key_id}",
                )
            self._signers[signer.key_id] = signer

    def verify(
        self,
        *,
        descriptor: IndustryIQGitHubReleaseDescriptor,
        artifact_digest: str,
        evidence_blob: bytes,
        evidence_source_ref: str,
        sbom_blob: bytes,
        sbom_source_ref: str,
    ) -> IndustryIQSupplyChainEvidence:
        try:
            token = evidence_blob.decode("utf-8").strip()
            header = jwt.get_unverified_header(token)
        except (UnicodeDecodeError, jwt.InvalidTokenError) as exc:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_JWS_INVALID",
                "Industry IQ release evidence is not a valid compact JWS.",
            ) from exc

        key_id = header.get("kid")
        algorithm = header.get("alg")
        if not isinstance(key_id, str) or not key_id:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_KEY_ID_REQUIRED",
                "Industry IQ release evidence JWS requires a trusted key ID.",
            )
        signer = self._signers.get(key_id)
        if signer is None:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_SIGNER_UNTRUSTED",
                f"Industry IQ release evidence signer is not trusted: {key_id}",
            )
        if not isinstance(algorithm, str) or algorithm not in signer.algorithms:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_ALGORITHM_NOT_ALLOWED",
                f"Industry IQ release evidence algorithm is not allowed: {algorithm!r}",
            )

        try:
            payload = jwt.decode(
                token,
                signer.public_key_pem,
                algorithms=[algorithm],
                options={"verify_aud": False},
            )
            claims = IndustryIQSignedReleaseEvidenceClaims.model_validate(payload)
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_SIGNATURE_INVALID",
                "Industry IQ release evidence signature or signed claims are invalid.",
            ) from exc

        if signer.publisher != descriptor.publisher or claims.publisher != descriptor.publisher:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_PUBLISHER_MISMATCH",
                "Signed release evidence publisher does not match the release descriptor.",
            )
        if claims.pack_id != descriptor.pack_id or claims.version != descriptor.version:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_IDENTITY_MISMATCH",
                "Signed release evidence pack identity does not match the release descriptor.",
            )
        if claims.subject_digest != artifact_digest:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_ARTIFACT_DIGEST_MISMATCH",
                "Signed release evidence does not bind the acquired artifact digest.",
            )

        sbom_digest = _sha256(sbom_blob)
        if claims.sbom.document_digest != sbom_digest:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_SBOM_DIGEST_MISMATCH",
                "Signed release evidence does not bind the acquired SBOM document.",
            )
        if claims.vulnerability_scan.sbom_document_digest != sbom_digest:
            raise IndustryIQSourceAdapterError(
                "PACK_EVIDENCE_VULNERABILITY_SBOM_MISMATCH",
                "Signed vulnerability evidence is not bound to the acquired SBOM document.",
            )

        return IndustryIQSupplyChainEvidence(
            publisher_attestation=IndustryIQPublisherAttestation(
                subject_digest=artifact_digest,
                publisher=descriptor.publisher,
                signer_identity=signer.signer_identity,
                signature_kind="other",
                signature_ref=evidence_source_ref,
                predicate_type=claims.predicate_type,
                verification="host_verified",
            ),
            sbom=IndustryIQSBOMEvidence(
                subject_digest=artifact_digest,
                document_digest=sbom_digest,
                format=claims.sbom.format,
                source_ref=sbom_source_ref,
                verification="host_verified",
            ),
            vulnerability_scan=IndustryIQVulnerabilityScan(
                subject_digest=artifact_digest,
                sbom_document_digest=sbom_digest,
                scanner=claims.vulnerability_scan.scanner,
                scanner_version=claims.vulnerability_scan.scanner_version,
                source_ref=evidence_source_ref,
                highest_severity=claims.vulnerability_scan.highest_severity,
                verification="host_verified",
            ),
        )


class GitHubReleaseIndustryIQSource:
    """Acquire and verify one pinned Industry IQ pack from a GitHub Release.

    Remote artifacts never become executable code. After release metadata, artifact bytes,
    JWS evidence and SBOM are verified, the declared pack identity is resolved only to a
    host-approved implementation supplied through ``IndustryIQPackResolver``.
    """

    def __init__(
        self,
        *,
        source_id: str,
        config: IndustryIQGitHubReleaseConfig,
        resolver: IndustryIQPackResolver,
        evidence_verifier: IndustryIQReleaseEvidenceVerifier,
        transport: IndustryIQReleaseTransport,
    ) -> None:
        if not source_id:
            raise IndustryIQSourceAdapterError(
                "PACK_SOURCE_ID_INVALID", "GitHub Release source ID cannot be empty."
            )
        if not _GITHUB_REPOSITORY.fullmatch(config.repository):
            raise IndustryIQSourceAdapterError(
                "PACK_SOURCE_REPOSITORY_INVALID",
                "GitHub repository must use owner/repository form.",
            )
        self.source_id = source_id
        self.config = config
        self.resolver = resolver
        self.evidence_verifier = evidence_verifier
        self.transport = transport

    def discover(self) -> Iterable[IndustryIQCatalogueCandidate]:
        release_url = (
            f"{_API_BASE}/repos/{self.config.repository}/releases/tags/"
            f"{quote(self.config.release_tag, safe='')}"
        )
        release = self.transport.get_json(release_url)
        release_id = release.get("id")
        tag_name = release.get("tag_name")
        if not isinstance(release_id, int) or tag_name != self.config.release_tag:
            raise IndustryIQSourceAdapterError(
                "PACK_RELEASE_IDENTITY_INVALID",
                "GitHub Release identity does not match the pinned source configuration.",
            )
        if self.config.expected_release_id is not None and release_id != self.config.expected_release_id:
            raise IndustryIQSourceAdapterError(
                "PACK_RELEASE_ID_MISMATCH",
                f"GitHub Release ID changed: expected={self.config.expected_release_id}, actual={release_id}.",
            )
        if release.get("draft") is True:
            raise IndustryIQSourceAdapterError(
                "PACK_RELEASE_DRAFT_REJECTED", "Draft GitHub Releases cannot supply Industry IQ packs."
            )
        if release.get("prerelease") is True and not self.config.allow_prerelease:
            raise IndustryIQSourceAdapterError(
                "PACK_RELEASE_PRERELEASE_REJECTED",
                "Prerelease GitHub Releases are disabled for this Industry IQ source.",
            )

        assets = _release_assets(release)
        descriptor_asset = _asset_by_name(assets, self.config.descriptor_asset_name)
        descriptor_blob = self.transport.get_bytes(
            _validated_asset_url(descriptor_asset, self.config.repository)
        )
        descriptor = _parse_descriptor(descriptor_blob)
        _require_sha256(descriptor.artifact_digest, "PACK_DESCRIPTOR_DIGEST_INVALID")

        artifact_asset = _asset_by_name(assets, descriptor.artifact_asset_name)
        artifact_url = _validated_asset_url(artifact_asset, self.config.repository)
        artifact_blob = self.transport.get_bytes(artifact_url)
        artifact_digest = _sha256(artifact_blob)
        if artifact_digest != descriptor.artifact_digest:
            raise IndustryIQSourceAdapterError(
                "PACK_ARTIFACT_DIGEST_MISMATCH",
                "Acquired GitHub Release artifact does not match its declared SHA-256 digest.",
            )

        evidence_asset = _asset_by_name(assets, descriptor.evidence_asset_name)
        evidence_url = _validated_asset_url(evidence_asset, self.config.repository)
        evidence_blob = self.transport.get_bytes(evidence_url)
        sbom_asset = _asset_by_name(assets, descriptor.sbom_asset_name)
        sbom_url = _validated_asset_url(sbom_asset, self.config.repository)
        sbom_blob = self.transport.get_bytes(sbom_url)

        source_ref = (
            f"github-release:{self.config.repository}@{self.config.release_tag}"
            f"#release={release_id}&asset={descriptor.artifact_asset_name}"
        )
        evidence = self.evidence_verifier.verify(
            descriptor=descriptor,
            artifact_digest=artifact_digest,
            evidence_blob=evidence_blob,
            evidence_source_ref=f"{source_ref}&evidence={descriptor.evidence_asset_name}",
            sbom_blob=sbom_blob,
            sbom_source_ref=f"{source_ref}&sbom={descriptor.sbom_asset_name}",
        )

        pack = self.resolver.resolve(descriptor.pack_id, descriptor.version)
        manifest = industry_iq_manifest(pack)
        if manifest.pack_id != descriptor.pack_id or manifest.version != descriptor.version:
            raise IndustryIQSourceAdapterError(
                "PACK_RESOLVER_IDENTITY_MISMATCH",
                "Resolved host pack implementation does not match verified release identity.",
            )

        return [
            IndustryIQCatalogueCandidate(
                pack=pack,
                provenance=IndustryIQPackProvenance(
                    source_id=self.source_id,
                    source_kind="repository",
                    source_ref=source_ref,
                    publisher=descriptor.publisher,
                    artifact_digest=artifact_digest,
                    verification="host_verified",
                    supply_chain=evidence,
                ),
            )
        ]


def _release_assets(release: Mapping[str, object]) -> list[Mapping[str, object]]:
    assets = release.get("assets")
    if not isinstance(assets, list) or not all(isinstance(item, Mapping) for item in assets):
        raise IndustryIQSourceAdapterError(
            "PACK_RELEASE_ASSETS_INVALID", "GitHub Release assets must be a JSON array of objects."
        )
    return list(assets)


def _asset_by_name(
    assets: Iterable[Mapping[str, object]], asset_name: str
) -> Mapping[str, object]:
    matches = [asset for asset in assets if asset.get("name") == asset_name]
    if len(matches) != 1:
        raise IndustryIQSourceAdapterError(
            "PACK_RELEASE_ASSET_NOT_UNIQUE",
            f"Expected exactly one GitHub Release asset named {asset_name!r}; found {len(matches)}.",
        )
    return matches[0]


def _validated_asset_url(asset: Mapping[str, object], repository: str) -> str:
    url = asset.get("url")
    prefix = f"{_API_BASE}/repos/{repository}/releases/assets/"
    if not isinstance(url, str) or not url.startswith(prefix):
        raise IndustryIQSourceAdapterError(
            "PACK_RELEASE_ASSET_URL_INVALID",
            "GitHub Release asset URL is outside the configured repository API scope.",
        )
    suffix = url[len(prefix) :]
    if not suffix.isdigit():
        raise IndustryIQSourceAdapterError(
            "PACK_RELEASE_ASSET_URL_INVALID",
            "GitHub Release asset URL must terminate in a numeric asset ID.",
        )
    return url


def _parse_descriptor(blob: bytes) -> IndustryIQGitHubReleaseDescriptor:
    try:
        raw = json.loads(blob.decode("utf-8"))
        return IndustryIQGitHubReleaseDescriptor.model_validate(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise IndustryIQSourceAdapterError(
            "PACK_RELEASE_DESCRIPTOR_INVALID",
            "GitHub Release Industry IQ descriptor is invalid.",
        ) from exc


def _sha256(blob: bytes) -> str:
    return f"sha256:{hashlib.sha256(blob).hexdigest()}"


def _require_sha256(value: str, code: str) -> None:
    if not _SHA256_DIGEST.fullmatch(value):
        raise IndustryIQSourceAdapterError(
            code,
            "Industry IQ release digest must use sha256:<64 hex characters>.",
        )
