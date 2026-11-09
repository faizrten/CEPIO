"""Cloud M0 lifecycle tests: no Azure or Cognite credentials or network required."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cognite_oid_m0_cloud import (
    CloudM0ConfigurationError,
    CloudM0IntegrityError,
    inventory_verdict,
    read_cloud_config,
    report_bytes,
    run_cloud_inventory,
    upload_verified_manifest,
)


def approved_env() -> dict[str, str]:
    return {
        "COGNITE_OID_PROJECT": "publicdata",
        "COGNITE_M2M_TENANT_ID": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "COGNITE_M2M_CLIENT_ID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "COGNITE_M2M_CLIENT_SECRET": "IN-MEMORY-TEST-ONLY",
        "AZURE_IDENTITY_CLIENT_ID": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "AZURE_BLOB_ACCOUNT_URL": "https://cepiotest.blob.core.windows.net",
        "AZURE_BLOB_CONTAINER": "oid-evidence",
    }


class FakeResource:
    def __init__(self, **attrs):
        self.attrs = attrs

    def dump(self, camel_case=True):
        assert camel_case
        return dict(self.attrs)


class FakeEndpoint:
    def __init__(self, rows, *, search=False):
        self.rows = rows
        self.search_enabled = search
        self.calls = []

    def list(self, *, limit, asset_ids=None):
        self.calls.append(("list", limit, asset_ids))
        if asset_ids:
            return [
                row
                for row in self.rows
                if row.attrs.get("assetId") in asset_ids
                or bool(set(row.attrs.get("assetIds", [])) & set(asset_ids))
            ][:limit]
        return self.rows[:limit]

    def search(self, *, name, limit):
        assert self.search_enabled
        self.calls.append(("search", name, limit))
        return [r for r in self.rows if name.lower() in r.attrs.get("name", "").lower()][:limit]

    def retrieve(self, *, id):
        self.calls.append(("retrieve", id))
        return next((r for r in self.rows if r.attrs.get("id") == id), None)


class FakeCdfClient:
    def __init__(self, *, project="publicdata", asset_name="Compressor A"):
        self.config = SimpleNamespace(project=project, base_url="https://api.cognitedata.com")
        self.assets = FakeEndpoint(
            [FakeResource(id=12, name=asset_name, lastUpdatedTime=1762000010000)],
            search=True,
        )
        self.time_series = FakeEndpoint(
            [
                FakeResource(
                    id=89,
                    name="Suction pressure",
                    assetId=12,
                    unit="bar",
                    lastUpdatedTime=1762000010000,
                )
            ]
        )
        self.events = FakeEndpoint([])
        self.files = FakeEndpoint([])


class FakeDownload:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


class FakeBlob:
    def __init__(self, *, corrupt=False):
        self.payload = None
        self.corrupt = corrupt
        self.upload_args = None

    def upload_blob(self, data, **kwargs):
        assert self.payload is None
        self.payload = data
        self.upload_args = kwargs

    def download_blob(self):
        assert self.payload is not None
        return FakeDownload(self.payload + (b"x" if self.corrupt else b""))


class FakeContainer:
    def __init__(self, *, corrupt=False):
        self.key = None
        self.blob = FakeBlob(corrupt=corrupt)

    def get_blob_client(self, path):
        assert self.key is None
        self.key = path
        return self.blob


def test_cloud_config_requires_separate_approved_machine_identity():
    data = approved_env()
    c = read_cloud_config(data)
    assert c.project == "publicdata"
    assert c.azure_identity_client_id == data["AZURE_IDENTITY_CLIENT_ID"]
    assert "IN-MEMORY-TEST-ONLY" not in repr(c)
    data["COGNITE_M2M_CLIENT_ID"] = "1b90ede3-271e-401b-81a0-a4d52bea3273"
    with pytest.raises(CloudM0ConfigurationError, match="interactive"):
        read_cloud_config(data)


@pytest.mark.parametrize(
    "updates",
    [
        {"COGNITE_OID_PROJECT": "private-tenant"},
        {"COGNITE_OID_AUTH_MODE": "interactive"},
        {"COGNITE_M2M_CLIENT_ID": ""},
        {"COGNITE_M2M_TENANT_ID": "not-a-uuid"},
        {"AZURE_BLOB_ACCOUNT_URL": "http://cepiotest.blob.core.windows.net"},
        {"AZURE_BLOB_ACCOUNT_URL": "https://untrusted.example"},
        {"AZURE_BLOB_ACCOUNT_URL": "https://cepiotest.blob.core.windows.net/secrets"},
        {"AZURE_BLOB_CONTAINER": "Invalid_Name"},
        {"COGNITE_OID_FOCUS": "../not-allowed"},
        {"COGNITE_OID_LIMIT": "201"},
        {"COGNITE_OID_FOCUS_LIMIT": "0"},
        {"COGNITE_OID_LIMIT": "abc"},
    ],
)
def test_cloud_configuration_fails_closed(updates):
    data = approved_env()
    data.update(updates)
    with pytest.raises(CloudM0ConfigurationError):
        read_cloud_config(data)


def test_cloud_execution_uploads_create_only_verified_receipt():
    config = read_cloud_config(approved_env())
    cdf = FakeCdfClient()
    container = FakeContainer()
    output = run_cloud_inventory(
        config,
        cdf_client=cdf,
        container_client=container,
        now=datetime(2026, 11, 9, tzinfo=timezone.utc),
        execution_id="run-test-0001",
    )
    assert output["verdict"] == "source-qualified-pending-engineering-review"
    assert output["cepio_runtime_registered"] == "false"
    assert output["industrial_decision_qualified"] == "false"
    assert container.key == "cepio/cognite-oid/m0/publicdata/2026/11/09/run-test-0001.json"
    assert container.blob.upload_args["overwrite"] is False
    assert container.blob.upload_args["blob_type"] == "BlockBlob"
    assert container.blob.upload_args["metadata"]["cepio_sha256"] == output["sha256"]
    assert len(output["sha256"]) == 64
    assert cdf.assets.calls[0][0] == "list"
    assert all(
        action in ("list", "search", "retrieve")
        for endpoint in (cdf.assets, cdf.time_series, cdf.events, cdf.files)
        for action, *_ in endpoint.calls
    )


def test_cloud_explicitly_distinguishes_source_from_scope_qualification():
    config = read_cloud_config(approved_env())
    container = FakeContainer()
    output = run_cloud_inventory(
        config,
        cdf_client=FakeCdfClient(asset_name="Area A"),
        container_client=container,
        execution_id="run-test-0002",
    )
    assert output["verdict"] == "needs-domain-review"
    assert container.blob.payload is not None


def test_cloud_upload_fails_on_storage_readback_corruption():
    data = approved_env()
    with pytest.raises(CloudM0IntegrityError, match="read-back digest"):
        run_cloud_inventory(
            read_cloud_config(data),
            cdf_client=FakeCdfClient(),
            container_client=FakeContainer(corrupt=True),
        )


def test_cloud_rejects_project_mismatch_before_azure_write():
    storage = FakeContainer()
    with pytest.raises(CloudM0IntegrityError, match="project"):
        run_cloud_inventory(
            read_cloud_config(approved_env()),
            cdf_client=FakeCdfClient(project="publicdatacdm"),
            container_client=storage,
        )
    assert storage.key is None


def test_cloud_rejects_unsafe_execution_context_before_source_read():
    config = read_cloud_config(approved_env())
    with pytest.raises(CloudM0ConfigurationError, match="timezone-aware"):
        run_cloud_inventory(
            config,
            cdf_client=FakeCdfClient(),
            container_client=FakeContainer(),
            now=datetime(2026, 11, 9),
        )
    with pytest.raises(CloudM0ConfigurationError, match="Unsafe cloud execution"):
        run_cloud_inventory(
            config,
            cdf_client=FakeCdfClient(),
            container_client=FakeContainer(),
            execution_id="../path",
        )


def test_report_limit_and_verdict_never_promote_undocumented_success():
    with pytest.raises(CloudM0IntegrityError, match="1 MiB"):
        report_bytes({"large": "x" * 1_048_577})
    report = {
        "binding_qualification": {"live_source_conformance": {"status": "blocked"}},
        "observations": {
            "focus_asset_count": 1,
            "focus_related_count": {"time_series": 1},
        },
    }
    assert inventory_verdict(report) == "blocked"
    report["binding_qualification"]["live_source_conformance"]["status"] = "passed"
    report["observations"]["focus_related_count"] = {"time_series": 0}
    assert inventory_verdict(report) == "needs-domain-review"


def test_verifier_denies_tamper_even_after_initial_upload():
    fake = FakeBlob(corrupt=True)
    with pytest.raises(CloudM0IntegrityError):
        upload_verified_manifest(
            fake,
            {"project": "publicdata", "snapshot_sha256": "test"},
            blob_path="cepio/cognite-oid/m0/publicdata/test.json",
        )
