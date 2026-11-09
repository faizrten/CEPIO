"""Offline, fail-closed Cognite OID M0 binding tests; never call the live tenant."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cepio.integrations.cognite.oid_m0 import (
    CogniteOIDM0Error,
    CogniteOIDEvidenceBinding,
    CogniteOIDSDKReader,
    run_oid_m0_inventory,
)
from cepio.management_contract import BindingDescriptor
from cepio.platform_bindings import qualify_evidence_binding, register_evidence_binding


class FakeResource:
    def __init__(self, **payload):
        self.payload = payload

    def dump(self, *, camel_case=True):
        assert camel_case is True
        return dict(self.payload)


ASSETS = [
    FakeResource(
        id=101, externalId="COMP-101", name="First Stage Gas Compressor",
        lastUpdatedTime=1762000000000, dataSetId=2,
    ),
    FakeResource(id=102, externalId="AS-102", name="Plant Area", lastUpdatedTime=1762000000100),
]
TIME_SERIES = [
    FakeResource(
        id=501, externalId="PT-501", name="Suction pressure", unit="bar",
        isString=False, assetId=101, lastUpdatedTime=1762000000500,
    ),
    FakeResource(
        id=502, externalId="VI-502", name="Vibration", isString=False,
        assetId=101, lastUpdatedTime=1762000000600,
    ),
]
EVENTS = [
    FakeResource(id=601, externalId="MAINT-1", name="Inspection", assetIds=[101], lastUpdatedTime=1762000000600)
]
FILES = [
    FakeResource(id=701, externalId="PID-1", name="Process P&ID", assetIds=[101], lastUpdatedTime=1762000000700)
]


class FakeEndpoint:
    def __init__(self, items, *, allows_search=False):
        self.items = items
        self.allows_search = allows_search
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        items = self.items
        if kwargs.get("asset_ids"):
            ids = set(kwargs["asset_ids"])
            items = [x for x in items if x.payload.get("assetId") in ids or ids.intersection(x.payload.get("assetIds", []))]
        return items[: kwargs["limit"]]

    def search(self, **kwargs):
        assert self.allows_search
        self.calls.append(("search", kwargs))
        return [x for x in self.items if kwargs["name"].lower() in x.payload.get("name", "").lower()][:kwargs["limit"]]

    def retrieve(self, *, id):
        self.calls.append(("retrieve", {"id": id}))
        return next((x for x in self.items if x.payload["id"] == id), None)


class FakeSDKClient:
    def __init__(self, *, project="publicdata", base_url="https://api.cognitedata.com"):
        self.config = SimpleNamespace(project=project, base_url=base_url)
        self.assets = FakeEndpoint(ASSETS, allows_search=True)
        self.time_series = FakeEndpoint(TIME_SERIES)
        self.events = FakeEndpoint(EVENTS)
        self.files = FakeEndpoint(FILES)


def _reader():
    return CogniteOIDSDKReader(FakeSDKClient())


def test_inventory_is_bounded_traceable_and_not_host_registered():
    reader = _reader()
    result = run_oid_m0_inventory(reader, limit=2, focus_phrase="compressor")
    assert result["schema_version"] == "cepio.cognite-oid-m0/0.1"
    assert result["observations"]["sampled"] == {"assets": 2, "time_series": 2, "events": 1, "files": 1}
    assert result["observations"]["missing_numeric_units"] == 1
    assert result["observations"]["history_window"].startswith("not yet established")
    assert result["binding_qualification"]["live_source_conformance"]["status"] == "passed"
    assert result["binding_qualification"]["host_registered"] is False
    assert result["binding_qualification"]["production_ready"] is False
    assert len(result["snapshot_sha256"]) == 64
    assert result == run_oid_m0_inventory(reader, limit=2, focus_phrase="compressor")
    assert all(method in ("list", "search", "retrieve") for api in (
        reader.client.assets, reader.client.time_series, reader.client.events, reader.client.files
    ) for method, _ in api.calls)


def test_binding_preserves_identity_and_source_timestamp_version():
    binding = CogniteOIDEvidenceBinding(_reader())
    reg = register_evidence_binding(binding, capability_id="industrial-evidence-inventory")
    assert reg.access_mode == "read"
    assert reg.authority == "observation-only"
    descriptor = BindingDescriptor.from_registration(reg)
    assert descriptor.provider == "cognite"
    result = qualify_evidence_binding(binding, external_id="assets/101")
    assert result.versioned is True
    assert "cognite-oid:asset:assets/101:1762000000000" == result.reference_key
    envelope = binding.resolve_evidence("assets/101")
    assert envelope.reference.dataset_id == "publicdata"
    assert envelope.evidence["name"] == "First Stage Gas Compressor"
    assert "metadata" not in envelope.evidence


@pytest.mark.parametrize("bad_id", ["", "assets", "unknown/101", "assets/-1", "assets/0", "assets/001", "assets/101/extra"])
def test_binding_rejects_noncanonical_resource_identity(bad_id):
    with pytest.raises(CogniteOIDM0Error):
        CogniteOIDEvidenceBinding(_reader()).resolve_evidence(bad_id)


def test_missing_version_is_a_hard_block_not_a_fabricated_revision():
    reader = _reader()
    reader.client.assets.items = [FakeResource(id=101, name="Compressor")]
    with pytest.raises(CogniteOIDM0Error, match="lastUpdatedTime"):
        CogniteOIDEvidenceBinding(reader).resolve_evidence("assets/101")
    result = run_oid_m0_inventory(reader, limit=2)
    assert result["binding_qualification"]["live_source_conformance"]["status"] == "blocked"


def test_project_host_and_limit_cannot_escape_open_data_boundary():
    for kwargs in (
        {"project": "customer-private"},
        {"base_url": "https://evil.example"},
        {"base_url": "http://api.cognitedata.com"},
    ):
        with pytest.raises(CogniteOIDM0Error):
            CogniteOIDSDKReader(FakeSDKClient(**kwargs))
    reader = _reader()
    with pytest.raises(CogniteOIDM0Error):
        reader.list_items("assets", limit=201)
    with pytest.raises(CogniteOIDM0Error):
        reader.list_items("other", limit=2)
    with pytest.raises(CogniteOIDM0Error):
        run_oid_m0_inventory(reader, limit=999)


def test_no_compressor_search_hit_does_not_invent_a_target():
    result = run_oid_m0_inventory(_reader(), limit=2, focus_phrase="nonexistent")
    assert result["observations"]["focus_asset_count"] == 0
    assert result["related_to_focus_assets"] == {}
    assert result["binding_qualification"]["live_source_conformance"]["status"] == "passed"
    # Binding qualification passes for a generic existing asset; compressor scope remains unqualified.
