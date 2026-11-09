"""One-shot Cognite OID M0 evidence snapshot from trusted GitHub Actions.

Only the already-authorized client-credentials OID_API is used. Real industrial
metadata is written to an Actions artifact, never to logs, and raw datapoints
and CDF mutations are forbidden by the underlying read-only M0 reader.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from cepio.integrations.cognite.oid_m0 import CogniteOIDSDKReader, run_oid_m0_inventory


OID_PROJECT = "publicdata"
OID_CLUSTER = "api"
OID_TENANT = "48d5043c-cf70-4c49-881c-c638f5796997"
OID_CLIENT = "1b90ede3-271e-401b-81a0-a4d52bea3273"


def summarize_inventory(report: dict) -> dict:
    """Sanitized, unambiguous M0 verdict; not proof of engineering value."""
    source = report["binding_qualification"]["live_source_conformance"]
    counts = report["observations"]
    source_passed = source["status"] == "passed"
    compressor_candidate = counts["focus_asset_count"] > 0
    linked_series = counts["focus_related_count"].get("time_series", 0) > 0
    return {
        "project": report["project"],
        "source_binding": "passed" if source_passed else "blocked",
        "scope": (
            "candidate-found-pending-expert-review"
            if source_passed and compressor_candidate and linked_series
            else "not-qualified"
        ),
        "sample_counts_not_totals": counts["sampled"],
        "compressor_candidates": counts["focus_asset_count"],
        "compressor_related_counts": counts["focus_related_count"],
        "unlinked_time_series_sample": counts["unlinked_time_series"],
        "missing_units_sample": counts["missing_numeric_units"],
        "manifest_sha256": report["snapshot_sha256"],
        "read_only": True,
        "production_ready": False,
    }


def save_artifact(path: Path, report: dict) -> None:
    """Create-only file readable to the invoking CI user; no stdout evidence."""
    path = path.resolve()
    if not path.parent.exists():
        raise ValueError("Trusted runner temporary directory does not exist")
    payload = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if len(payload) > 1_048_576:
        raise ValueError("M0 snapshot exceeds 1 MiB artifact cap")
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)


def main() -> int:
    secret = os.environ.get("OID_API", "")
    if not secret or "\n" in secret or "\r" in secret:
        print('{"status":"blocked","reason":"OID_API-unavailable"}')
        return 2
    try:
        from cognite.client import CogniteClient

        client = CogniteClient.default_oauth_client_credentials(
            project=OID_PROJECT,
            cdf_cluster=OID_CLUSTER,
            tenant_id=OID_TENANT,
            client_id=OID_CLIENT,
            client_secret=secret,
            client_name="cepio-m0-trusted-github-inventory",
        )
        report = run_oid_m0_inventory(CogniteOIDSDKReader(client), focus_phrase="compressor")
        folder = Path(os.environ["RUNNER_TEMP"])
        save_artifact(folder / "cepio-oid-m0-publicdata.json", report)
        summary = summarize_inventory(report)
    except Exception as exc:
        # SDK network error strings can contain source / HTTP details: do not print.
        print(json.dumps({"status": "blocked", "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["source_binding"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
