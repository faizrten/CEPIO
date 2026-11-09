"""Read-only Cognite Open Industrial Data inventory and CEPIO binding qualification.

This module never reads raw datapoints, downloads files or calls provider write APIs.
It does not register a binding in a CEPIO host. Source facts stay in Cognite.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol
from urllib.parse import urlparse

from ...domain_bindings import ExternalRecordReference
from ...platform_bindings import (
    BindingCapability,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
    qualify_evidence_binding,
    register_evidence_binding,
)

OID_PROJECTS = frozenset({"publicdata", "publicdatacdm"})
OID_BASE_URL = "https://api.cognitedata.com"
KINDS = ("assets", "time_series", "events", "files")
RESOURCE_TYPES = {
    "assets": "asset",
    "time_series": "time-series",
    "events": "event",
    "files": "file-metadata",
}
VISIBLE_FIELDS = (
    "id",
    "externalId",
    "name",
    "unit",
    "assetId",
    "assetIds",
    "isString",
    "isStep",
    "startTime",
    "endTime",
    "type",
    "subtype",
    "mimeType",
    "dataSetId",
    "lastUpdatedTime",
)


class CogniteOIDM0Error(ValueError):
    """Fail-closed invalid configuration, resource identity or provenance."""


class CogniteOIDReader(Protocol):
    project: str

    def list_items(
        self, kind: str, *, limit: int, asset_ids: list[int] | None = None
    ) -> list[dict[str, Any]]: ...

    def search_assets(self, phrase: str, *, limit: int) -> list[dict[str, Any]]: ...

    def retrieve_item(self, kind: str, *, cdf_id: int) -> dict[str, Any] | None: ...


class CogniteOIDSDKReader:
    """Narrow SDK adapter; only list, search and retrieve metadata methods are used."""

    def __init__(self, client: Any) -> None:
        project = str(client.config.project)
        base_url = str(client.config.base_url).rstrip("/")
        parsed = urlparse(base_url)
        if project not in OID_PROJECTS or parsed.scheme != "https" or base_url != OID_BASE_URL:
            raise CogniteOIDM0Error("M0 permits only Cognite OID projects on the api cluster")
        self.client = client
        self.project = project

    def _api(self, kind: str) -> Any:
        if kind not in KINDS:
            raise CogniteOIDM0Error(f"Unsupported Cognite OID resource type: {kind}")
        return getattr(self.client, kind)

    def list_items(
        self, kind: str, *, limit: int, asset_ids: list[int] | None = None
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise CogniteOIDM0Error("M0 list limit must be between 1 and 200")
        if kind == "assets" and asset_ids:
            raise CogniteOIDM0Error("Assets inventory does not accept asset_ids")
        kwargs: dict[str, Any] = {"limit": limit}
        if asset_ids:
            if kind not in ("time_series", "events", "files") or len(asset_ids) > 10:
                raise CogniteOIDM0Error("Invalid bounded asset filter")
            kwargs["asset_ids"] = asset_ids
        return [item.dump(camel_case=True) for item in self._api(kind).list(**kwargs)]

    def search_assets(self, phrase: str, *, limit: int) -> list[dict[str, Any]]:
        if not phrase.strip() or not 1 <= limit <= 100:
            raise CogniteOIDM0Error("Asset search requires a phrase and a limit up to 100")
        return [
            item.dump(camel_case=True)
            for item in self.client.assets.search(name=phrase, limit=limit)
        ]

    def retrieve_item(self, kind: str, *, cdf_id: int) -> dict[str, Any] | None:
        if not isinstance(cdf_id, int) or isinstance(cdf_id, bool) or cdf_id <= 0:
            raise CogniteOIDM0Error("CDF resource ID must be a positive integer")
        item = self._api(kind).retrieve(id=cdf_id)
        return item.dump(camel_case=True) if item is not None else None


class CogniteOIDEvidenceBinding:
    """Source-neutral, versioned, observation-only evidence from Cognite OID."""

    manifest = PlatformBindingManifest(
        binding_id="cepio.binding.cognite.oid-m0",
        provider_id="cognite",
        source_system="cognite-oid",
        mode=BindingMode.evidence,
        capabilities=frozenset(
            {BindingCapability.resolve_evidence, BindingCapability.versioned_identity}
        ),
    )

    def __init__(self, reader: CogniteOIDReader) -> None:
        if reader.project not in OID_PROJECTS:
            raise CogniteOIDM0Error("Unsupported project; OID only")
        self.reader = reader

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        # Canonical identity: '<resource-kind>/<immutable CDF numeric ID>'.
        parts = external_id.split("/")
        if len(parts) != 2 or parts[0] not in KINDS or not parts[1].isdigit():
            raise CogniteOIDM0Error("Expected <kind>/<positive CDF numeric ID>")
        kind, id_text = parts
        cdf_id = int(id_text)
        if cdf_id <= 0 or str(cdf_id) != id_text:
            raise CogniteOIDM0Error("Non-canonical CDF resource identity")
        item = self.reader.retrieve_item(kind, cdf_id=cdf_id)
        if item is None or item.get("id") != cdf_id:
            raise CogniteOIDM0Error("CDF evidence is missing or returned a different identity")
        updated = item.get("lastUpdatedTime")
        if not isinstance(updated, int) or isinstance(updated, bool) or updated <= 0:
            raise CogniteOIDM0Error("CDF record has no trustworthy lastUpdatedTime version")
        projection = _public_projection(item)
        return EvidenceEnvelope(
            reference=ExternalRecordReference(
                source_system=self.manifest.source_system,
                record_kind=RESOURCE_TYPES[kind],
                record_id=external_id,
                source_service="Cognite Data Fusion OID v1",
                record_version=str(updated),
                dataset_id=self.reader.project,
                metadata={"cdf_resource_kind": kind, "cdf_numeric_id": str(cdf_id)},
            ),
            evidence=projection,
        )


def _public_projection(item: dict[str, Any]) -> dict[str, Any]:
    """Allowlist metadata, excluding raw payloads, credentials and free-form metadata maps."""
    return {key: item[key] for key in VISIBLE_FIELDS if key in item}


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # CDF's unfiltered list order is not a semantic ranking; canonicalize evidence output.
    return sorted((_public_projection(item) for item in items), key=lambda x: str(x.get("id", "")))


def run_oid_m0_inventory(
    reader: CogniteOIDReader,
    *,
    limit: int = 100,
    focus_phrase: str = "compressor",
    focus_limit: int = 20,
) -> dict[str, Any]:
    """Collect a bounded snapshot and qualify one live source record without writing to CDF."""
    if reader.project not in OID_PROJECTS:
        raise CogniteOIDM0Error("M0 is restricted to the Cognite OID projects")
    if not 1 <= limit <= 200 or not 1 <= focus_limit <= 100:
        raise CogniteOIDM0Error("M0 inventory limits exceeded")

    resources = {kind: _sort_items(reader.list_items(kind, limit=limit)) for kind in KINDS}
    focused = _sort_items(reader.search_assets(focus_phrase, limit=focus_limit))
    related_ids = [
        item["id"] for item in focused if isinstance(item.get("id"), int) and item["id"] > 0
    ][:10]
    related: dict[str, list[dict[str, Any]]] = {}
    if related_ids:
        for kind in ("time_series", "events", "files"):
            related[kind] = _sort_items(reader.list_items(kind, limit=limit, asset_ids=related_ids))

    binding = CogniteOIDEvidenceBinding(reader)
    registration = register_evidence_binding(binding, capability_id="industrial-evidence-inventory")
    candidate = next(
        (r for r in focused + resources["assets"] if isinstance(r.get("id"), int)),
        None,
    )
    proof: dict[str, Any] = {"status": "blocked", "reason": "no asset ID available"}
    if candidate is not None:
        record_id = f"assets/{candidate['id']}"
        try:
            conformance = qualify_evidence_binding(binding, external_id=record_id)
        except (CogniteOIDM0Error, ValueError, KeyError) as exc:
            proof = {"status": "blocked", "record_id": record_id, "reason": str(exc)}
        else:
            proof = {
                "status": "passed",
                "record_id": record_id,
                "reference_key": conformance.reference_key,
                "versioned": conformance.versioned,
            }

    observations = {
        "sampled": {kind: len(items) for kind, items in resources.items()},
        "focus_asset_count": len(focused),
        "focus_related_count": {kind: len(items) for kind, items in related.items()},
        "missing_numeric_units": sum(
            1
            for item in resources["time_series"]
            if item.get("isString") is False and not item.get("unit")
        ),
        "unlinked_time_series": sum(
            1 for item in resources["time_series"] if not item.get("assetId")
        ),
        "history_window": "not yet established; raw datapoints deliberately excluded",
        "coverage": "bounded samples, NOT full project counts",
    }
    source_snapshot = {
        "schema_version": "cepio.cognite-oid-m0/0.1",
        "project": reader.project,
        "provider": "cognite",
        "limits": {"per_resource": limit, "focus_search": focus_limit, "linked_assets": 10},
        "focus_phrase": focus_phrase,
        "resources": resources,
        "focused_assets": focused,
        "related_to_focus_assets": related,
        "observations": observations,
        "binding_qualification": {
            "binding_id": registration.manifest.binding_id,
            "contract_version": registration.contract_version,
            "access_mode": registration.access_mode,
            "authority": registration.authority,
            "declared_capabilities": list(registration.declared_capabilities),
            "live_source_conformance": proof,
            "host_registered": False,
            "production_ready": False,
        },
    }
    digest = hashlib.sha256(
        json.dumps(
            source_snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return {**source_snapshot, "snapshot_sha256": digest}
