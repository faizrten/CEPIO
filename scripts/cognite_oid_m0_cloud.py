"""Cloud-only, read-only Cognite OID M0 inventory with Azure Blob evidence receipts.

Cloud authentication is deliberately *not* Cognite's public interactive OID app.
An explicitly authorized Cognite M2M identity is required. This script is not
an agent endpoint, an Azure provisioning tool or a producer of industrial decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
from typing import Any, Mapping
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from cepio.integrations.cognite.oid_m0 import (
    CogniteOIDSDKReader,
    OID_PROJECTS,
    run_oid_m0_inventory,
)

# These identifiers belong to Cognite's delegated/interactive public OID apps.
# Never silently use them as unattended client-credentials identities.
PUBLIC_OID_CLIENT_IDS = frozenset(
    {"1b90ede3-271e-401b-81a0-a4d52bea3273", "dea6bb8d-0f48-4bf0-a469-176fc19edc14"}
)
MAX_REPORT_BYTES = 1_048_576


class CloudM0ConfigurationError(ValueError):
    """Fail closed on missing cloud identity, source authorization or storage scope."""


class CloudM0IntegrityError(RuntimeError):
    """Storage did not preserve exactly the expected inventory manifest."""


@dataclass(frozen=True)
class CloudM0Config:
    project: str
    m2m_tenant_id: str
    m2m_client_id: str
    m2m_client_secret: str = field(repr=False)
    azure_identity_client_id: str
    storage_account_url: str
    storage_container: str
    focus_phrase: str = "compressor"
    limit: int = 100
    focus_limit: int = 20


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise CloudM0ConfigurationError(f"Cloud M0 requires {key}")
    return value


def _guid(value: str, key: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise CloudM0ConfigurationError(f"{key} must be a UUID") from exc


def read_cloud_config(env: Mapping[str, str]) -> CloudM0Config:
    """Parse explicit cloud config; never accept a public delegated OID app as M2M."""
    project = env.get("COGNITE_OID_PROJECT", "publicdata").strip()
    if project not in OID_PROJECTS:
        raise CloudM0ConfigurationError("Only Cognite Open Industrial Data projects are permitted")
    if env.get("COGNITE_OID_AUTH_MODE", "client-credentials") != "client-credentials":
        raise CloudM0ConfigurationError(
            "Cloud M0 requires approved client-credentials authentication"
        )
    tenant = _guid(_required(env, "COGNITE_M2M_TENANT_ID"), "COGNITE_M2M_TENANT_ID")
    client = _guid(_required(env, "COGNITE_M2M_CLIENT_ID"), "COGNITE_M2M_CLIENT_ID")
    if client in PUBLIC_OID_CLIENT_IDS:
        raise CloudM0ConfigurationError(
            "Public OID app is interactive, not an approved M2M identity"
        )
    identity = _guid(_required(env, "AZURE_IDENTITY_CLIENT_ID"), "AZURE_IDENTITY_CLIENT_ID")
    url = _required(env, "AZURE_BLOB_ACCOUNT_URL").rstrip("/")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not re.fullmatch(r"[a-z0-9]{3,24}\.blob\.core\.windows\.net", parsed.netloc)
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
    ):
        raise CloudM0ConfigurationError("Azure Blob endpoint must be a direct HTTPS account URL")
    container = _required(env, "AZURE_BLOB_CONTAINER")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?", container):
        raise CloudM0ConfigurationError("Azure Blob container name is invalid")
    focus = env.get("COGNITE_OID_FOCUS", "compressor").strip()
    if not 1 <= len(focus) <= 80 or not re.fullmatch(r"[a-zA-Z0-9 _-]+", focus):
        raise CloudM0ConfigurationError("Invalid bounded compressor focus phrase")
    try:
        limit = int(env.get("COGNITE_OID_LIMIT", "100"))
        focus_limit = int(env.get("COGNITE_OID_FOCUS_LIMIT", "20"))
    except ValueError as exc:
        raise CloudM0ConfigurationError("M0 limits must be integers") from exc
    if not 1 <= limit <= 200 or not 1 <= focus_limit <= 100:
        raise CloudM0ConfigurationError("M0 sampling limits exceeded")
    return CloudM0Config(
        project=project,
        m2m_tenant_id=tenant,
        m2m_client_id=client,
        m2m_client_secret=_required(env, "COGNITE_M2M_CLIENT_SECRET"),
        azure_identity_client_id=identity,
        storage_account_url=url,
        storage_container=container,
        focus_phrase=focus,
        limit=limit,
        focus_limit=focus_limit,
    )


def report_bytes(report: dict[str, Any]) -> bytes:
    payload = (
        json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise CloudM0IntegrityError("Bounded M0 manifest exceeds the 1 MiB cloud receipt limit")
    return payload


def inventory_verdict(report: dict[str, Any]) -> str:
    """A general source conformance pass is NOT proof of compressor scope."""
    if report["binding_qualification"]["live_source_conformance"]["status"] != "passed":
        return "blocked"
    if (
        report["observations"]["focus_asset_count"] == 0
        or report["observations"]["focus_related_count"].get("time_series", 0) == 0
    ):
        return "needs-domain-review"
    return "source-qualified-pending-engineering-review"


def upload_verified_manifest(
    blob_client: Any,
    report: dict[str, Any],
    *,
    blob_path: str,
    content_settings: Any = None,
) -> str:
    """Create-only Block Blob; read back the actual bytes before claiming storage success."""
    payload = report_bytes(report)
    digest = hashlib.sha256(payload).hexdigest()
    blob_client.upload_blob(
        payload,
        blob_type="BlockBlob",
        overwrite=False,
        content_settings=content_settings,
        metadata={
            "cepio_sha256": digest,
            "cepio_m0_project": report["project"],
            "cepio_source": "cognite-oid",
        },
    )
    actual = blob_client.download_blob().readall()
    if len(actual) > MAX_REPORT_BYTES or hashlib.sha256(actual).hexdigest() != digest:
        raise CloudM0IntegrityError("Azure Blob read-back digest differs from M0 report")
    return digest


def run_cloud_inventory(
    config: CloudM0Config,
    *,
    cdf_client: Any,
    container_client: Any,
    now: datetime | None = None,
    execution_id: str | None = None,
    content_settings: Any = None,
) -> dict[str, str]:
    """One M0 execution, with fixed bounds and verified Azure artifact persistence."""
    run_time = now or datetime.now(timezone.utc)
    if run_time.tzinfo is None:
        raise CloudM0ConfigurationError("Cloud M0 requires timezone-aware run time")
    run_id = execution_id or uuid4().hex
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", run_id):
        raise CloudM0ConfigurationError("Unsafe cloud execution identifier")
    report = run_oid_m0_inventory(
        CogniteOIDSDKReader(cdf_client),
        limit=config.limit,
        focus_phrase=config.focus_phrase,
        focus_limit=config.focus_limit,
    )
    if report["project"] != config.project:
        raise CloudM0IntegrityError("CDF evidence project does not match approved cloud project")
    verdict = inventory_verdict(report)
    path = f"cepio/cognite-oid/m0/{config.project}/{run_time.strftime('%Y/%m/%d')}/{run_id}.json"
    digest = upload_verified_manifest(
        container_client.get_blob_client(path),
        report,
        blob_path=path,
        content_settings=content_settings,
    )
    return {
        "verdict": verdict,
        "project": config.project,
        "blob_path": path,
        "sha256": digest,
        "evidence_manifest_sha256": report["snapshot_sha256"],
        "cepio_runtime_registered": "false",
        "industrial_decision_qualified": "false",
    }


def main() -> int:
    try:
        config = read_cloud_config(os.environ)
        # Dependencies are opt-in for the dedicated cloud image; Core remains unchanged.
        from azure.identity import ManagedIdentityCredential
        from azure.storage.blob import BlobServiceClient, ContentSettings
        from cognite.client import CogniteClient

        # Explicit user-assigned identity for storage, not an ambient developer credential.
        azure_credential = ManagedIdentityCredential(client_id=config.azure_identity_client_id)
        blob_service = BlobServiceClient(
            account_url=config.storage_account_url, credential=azure_credential
        )
        cdf_client = CogniteClient.default_oauth_client_credentials(
            project=config.project,
            cdf_cluster="api",
            tenant_id=config.m2m_tenant_id,
            client_id=config.m2m_client_id,
            client_secret=config.m2m_client_secret,
            client_name="cepio-cognite-oid-m0-cloud",
        )
        result = run_cloud_inventory(
            config,
            cdf_client=cdf_client,
            container_client=blob_service.get_container_client(config.storage_container),
            content_settings=ContentSettings(content_type="application/json"),
        )
    except Exception as exc:
        # Provider SDK exceptions may include request or identity details; never log them.
        print(f"Cloud M0 blocked: {type(exc).__name__}", file=sys.stderr)
        return 2
    # Only safe metadata is logged. No source records, bearer tokens or secrets.
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "source-qualified-pending-engineering-review" else 3


if __name__ == "__main__":
    raise SystemExit(main())
