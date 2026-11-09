"""Offline M0 readiness, evidence snapshot, and secret handoff guard tests."""

from __future__ import annotations

from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cognite_oid_azure_readiness import collect_readiness  # noqa: E402
from cognite_oid_m0_github import save_artifact, summarize_inventory  # noqa: E402


def fixture_report(*, source_passed=True, compressors=1, series=2):
    return {
        "project": "publicdata",
        "snapshot_sha256": "a" * 64,
        "binding_qualification": {
            "live_source_conformance": {"status": "passed" if source_passed else "blocked"}
        },
        "observations": {
            "sampled": {"assets": 100, "time_series": 100, "events": 42, "files": 80},
            "focus_asset_count": compressors,
            "focus_related_count": {"time_series": series},
            "missing_numeric_units": 4,
            "unlinked_time_series": 7,
        },
    }


def test_inventory_summary_does_not_claim_prod_or_decision_readiness():
    result = summarize_inventory(fixture_report())
    assert result["project"] == "publicdata"
    assert result["source_binding"] == "passed"
    assert result["scope"] == "candidate-found-pending-expert-review"
    assert result["read_only"] is True
    assert result["production_ready"] is False
    assert result["compressor_candidates"] == 1
    assert result["sample_counts_not_totals"]["assets"] == 100
    assert "asset_identity" not in result
    assert len(result["manifest_sha256"]) == 64


@pytest.mark.parametrize(
    "source_passed,compressors,series",
    [(False, 1, 1), (True, 0, 1), (True, 1, 0)],
)
def test_inventory_summary_fails_closed_on_missing_scope(source_passed, compressors, series):
    result = summarize_inventory(
        fixture_report(source_passed=source_passed, compressors=compressors, series=series)
    )
    assert result["scope"] == "not-qualified"


def test_inventory_snapshot_is_create_only_and_not_world_readable(tmp_path):
    path = tmp_path / "oid-inventory.json"
    data = fixture_report()
    save_artifact(path, data)
    actual = json.loads(path.read_text(encoding="utf-8"))
    assert actual == data
    assert not (path.stat().st_mode & 0o077)
    with pytest.raises(FileExistsError):
        save_artifact(path, data)


def test_inventory_snapshot_denies_nonexisting_parent_and_excessive_size(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        save_artifact(tmp_path / "missing" / "inventory.json", fixture_report())
    with pytest.raises(ValueError, match="1 MiB"):
        save_artifact(tmp_path / "inventory.json", {"large": "x" * 1_048_577})


def test_azure_readiness_never_claims_identity_or_blob_rights():
    commands = []

    def approve(cmd):
        commands.append(cmd)
        return True

    result = collect_readiness(approve)
    assert result["status"] == "existing-resources-visible"
    assert len(commands) == 4
    assert all(cmd[0] in ("group", "containerapp", "acr", "keyvault") for cmd in commands)
    assert all(flag == "visible" for flag in result["checks"].values())
    assert result["identity_scope_qualified"] is False
    assert result["blob_container_qualified"] is False
    assert result["source_secret_transferred"] is False
    assert result["azure_resources_modified"] is False


def test_azure_readiness_failure_is_not_missing_resource_claim():
    result = collect_readiness(lambda cmd: cmd[0] == "group")
    assert result["status"] == "review-azure-access"
    assert result["checks"]["container_registry"] == "not-verified"


def test_secret_handoff_requires_trusted_main_and_protected_environment():
    root = Path(__file__).resolve().parents[1]
    handoff = (root / ".github/workflows/cognite-oid-secret-handoff.yml").read_text()
    assert "workflow_dispatch" in handoff
    assert "push:" not in handoff
    assert "environment: cognite-m0" in handoff
    assert "github.ref == 'refs/heads/main'" in handoff
    assert 'M0_HANDOFF_APPROVED" == "true"' in handoff
    assert 'M0_AUTH_APPROVED" == "true"' in handoff
    assert "secrets.OID_API" in handoff
    assert "--file " in handoff
    assert "--value" not in handoff
    assert "mktemp /dev/shm/" in handoff
    assert "az keyvault secret set" in handoff
    assert "az deployment group create" not in handoff
    assert "az containerapp job start" not in handoff
    assert "upload-artifact" not in handoff


def test_source_inventory_and_azure_probe_are_main_only_and_minimal():
    root = Path(__file__).resolve().parents[1]
    a = (root / ".github/workflows/cognite-oid-m0-inventory.yml").read_text()
    b = (root / ".github/workflows/cognite-oid-azure-readiness.yml").read_text()
    assert "github.ref == 'refs/heads/main'" in a
    assert "github.ref == 'refs/heads/main'" in b
    assert "secrets.OID_API" in a
    assert "environment: azure-demo" in b
    assert "secrets.OID_API" not in b
    assert "workflow_dispatch" in a and "workflow_dispatch" in b
    assert "pull_request_target" not in a
    assert "pull_request_target" not in b
    assert "retention-days: 7" in a
