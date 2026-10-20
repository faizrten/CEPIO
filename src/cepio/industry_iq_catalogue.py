from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from ._version import __version__
from .industry_iq import (
    IndustryIQDeploymentManifest,
    IndustryIQPack,
    IndustryIQPackManifest,
    IndustryIQPackRegistry,
    industry_iq_manifest,
)
from .runtime import CEPIORuntime


_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


class IndustryIQCatalogueError(ValueError):
    """Fail-closed catalogue discovery, provenance, or trust-policy failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IndustryIQPackProvenance(BaseModel):
    """Host-asserted provenance for one discovered Industry IQ pack artifact.

    ``host_verified`` means the source adapter verified the referenced artifact before
    handing the candidate to CEPIO Core. Core does not fetch remote artifacts or infer
    cryptographic trust from a self-declared digest.
    """

    source_id: str = Field(min_length=1)
    source_kind: Literal["builtin", "repository", "package", "filesystem", "other"]
    source_ref: str = Field(min_length=1)
    publisher: str | None = None
    artifact_digest: str | None = None
    verification: Literal["builtin", "host_verified", "unverified"] = "unverified"


class IndustryIQTrustPolicy(BaseModel):
    """Host-configured admission policy for catalogue candidates."""

    trusted_source_ids: set[str] = Field(default_factory=set)
    trusted_publishers: set[str] = Field(default_factory=set)
    require_digest_for_external: bool = True

    def validate(self, provenance: IndustryIQPackProvenance) -> None:
        if provenance.source_id not in self.trusted_source_ids:
            raise IndustryIQCatalogueError(
                "PACK_SOURCE_UNTRUSTED",
                f"Industry IQ source is not trusted: {provenance.source_id}",
            )

        if provenance.verification == "unverified":
            raise IndustryIQCatalogueError(
                "PACK_PROVENANCE_UNVERIFIED",
                f"Industry IQ pack provenance is not host-verified: {provenance.source_ref}",
            )
        if provenance.verification == "builtin" and provenance.source_kind != "builtin":
            raise IndustryIQCatalogueError(
                "PACK_PROVENANCE_INVALID",
                "Only builtin catalogue sources may use builtin provenance verification.",
            )

        if self.trusted_publishers:
            if provenance.publisher not in self.trusted_publishers:
                raise IndustryIQCatalogueError(
                    "PACK_PUBLISHER_UNTRUSTED",
                    f"Industry IQ publisher is not trusted: {provenance.publisher!r}",
                )

        external = provenance.source_kind != "builtin"
        if self.require_digest_for_external and external and provenance.artifact_digest is None:
            raise IndustryIQCatalogueError(
                "PACK_DIGEST_REQUIRED",
                f"External Industry IQ pack requires a verified artifact digest: {provenance.source_ref}",
            )
        if provenance.artifact_digest is not None and not _SHA256_DIGEST.fullmatch(
            provenance.artifact_digest
        ):
            raise IndustryIQCatalogueError(
                "PACK_DIGEST_INVALID",
                "Industry IQ artifact digest must use sha256:<64 hex characters>.",
            )


@dataclass(frozen=True)
class IndustryIQCatalogueCandidate:
    """Runtime pack plus host-supplied provenance discovered from one source."""

    pack: IndustryIQPack
    provenance: IndustryIQPackProvenance


class IndustryIQCatalogueSource(Protocol):
    """Host-side source adapter. Agents never receive this discovery capability."""

    source_id: str

    def discover(self) -> Iterable[IndustryIQCatalogueCandidate]: ...


class IndustryIQCatalogueRecord(BaseModel):
    """Serializable trusted-catalogue record."""

    manifest: IndustryIQPackManifest
    provenance: IndustryIQPackProvenance


class IndustryIQCatalogueDeployment(BaseModel):
    """Registry deployment evidence enriched with trusted pack provenance."""

    deployment: IndustryIQDeploymentManifest
    provenance: dict[str, IndustryIQPackProvenance]


class IndustryIQCatalogue:
    """Host-controlled trusted catalogue layered around the v0.5 pack registry.

    Discovery and trust admission are side-effect free with respect to the runtime.
    A source batch is admitted atomically: one invalid or conflicting candidate rejects
    the entire batch. Installation remains delegated to ``IndustryIQPackRegistry`` so
    dependency, compatibility and capability-collision invariants stay centralized.
    """

    def __init__(
        self,
        trust_policy: IndustryIQTrustPolicy,
        *,
        core_version: str = __version__,
    ) -> None:
        self.trust_policy = trust_policy
        self.core_version = core_version
        self._packs: dict[tuple[str, str], IndustryIQPack] = {}
        self._records: dict[tuple[str, str], IndustryIQCatalogueRecord] = {}

    def ingest(self, source: IndustryIQCatalogueSource) -> None:
        if not source.source_id:
            raise IndustryIQCatalogueError(
                "CATALOGUE_SOURCE_ID_INVALID", "Industry IQ catalogue source ID cannot be empty."
            )

        staged_packs: dict[tuple[str, str], IndustryIQPack] = {}
        staged_records: dict[tuple[str, str], IndustryIQCatalogueRecord] = {}

        for candidate in source.discover():
            provenance = candidate.provenance
            if provenance.source_id != source.source_id:
                raise IndustryIQCatalogueError(
                    "CATALOGUE_SOURCE_MISMATCH",
                    (
                        f"Candidate source {provenance.source_id} does not match "
                        f"adapter source {source.source_id}."
                    ),
                )
            self.trust_policy.validate(provenance)
            manifest = industry_iq_manifest(candidate.pack)
            key = (manifest.pack_id, manifest.version)
            record = IndustryIQCatalogueRecord(manifest=manifest, provenance=provenance)

            existing = self._records.get(key) or staged_records.get(key)
            if existing is not None:
                if existing == record:
                    raise IndustryIQCatalogueError(
                        "CATALOGUE_PACK_ALREADY_PRESENT",
                        f"Industry IQ pack already present in catalogue: {manifest.pack_id}@{manifest.version}",
                    )
                raise IndustryIQCatalogueError(
                    "CATALOGUE_PACK_PROVENANCE_CONFLICT",
                    (
                        "Conflicting provenance for Industry IQ pack "
                        f"{manifest.pack_id}@{manifest.version}."
                    ),
                )

            staged_packs[key] = candidate.pack
            staged_records[key] = record

        self._packs.update(staged_packs)
        self._records.update(staged_records)

    def records(self) -> list[IndustryIQCatalogueRecord]:
        return [
            self._records[key]
            for key in sorted(self._records, key=lambda item: (item[0], item[1]), reverse=False)
        ]

    def build_registry(self) -> IndustryIQPackRegistry:
        registry = IndustryIQPackRegistry(core_version=self.core_version)
        for key in sorted(self._packs):
            registry.register(self._packs[key])
        return registry

    def install(
        self,
        runtime: CEPIORuntime,
        requested: Iterable[str] | Mapping[str, str],
    ) -> IndustryIQCatalogueDeployment:
        registry = self.build_registry()
        deployment = registry.install(runtime, requested)
        provenance = {
            pack_id: self._records[(pack_id, manifest.version)].provenance
            for pack_id, manifest in sorted(deployment.packs.items())
        }
        result = IndustryIQCatalogueDeployment(
            deployment=deployment,
            provenance=provenance,
        )
        setattr(runtime, "industry_iq_catalogue_deployment", result)
        return result
