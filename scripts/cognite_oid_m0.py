"""Execute the Cognite Open Industrial Data M0 inventory; read-only and bounded.

Install with: python -m pip install -e . && python -m pip install 'cognite-sdk>=8,<9'
Use OAuthInteractive locally, or set COGNITE_OID_ACCESS_TOKEN in your own shell.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from cepio.integrations.cognite.oid_m0 import (
    CogniteOIDSDKReader,
    OID_PROJECTS,
    run_oid_m0_inventory,
)

OID_TENANT = "48d5043c-cf70-4c49-881c-c638f5796997"
OID_CLIENT_ID = "1b90ede3-271e-401b-81a0-a4d52bea3273"


def build_client(project: str, *, auth: str):
    """Authenticate locally. Neither tokens nor credentials are persisted in reports."""
    try:
        from cognite.client import CogniteClient
        from cognite.client.credentials import Token
    except ImportError as exc:
        raise RuntimeError("Install cognite-sdk>=8,<9 to run the live M0 inventory") from exc
    if auth == "env":
        token = os.environ.get("COGNITE_OID_ACCESS_TOKEN", "").strip()
        if not token:
            raise RuntimeError("COGNITE_OID_ACCESS_TOKEN must be set for --auth env")
        return CogniteClient.default(
            project=project,
            cdf_cluster="api",
            credentials=Token(lambda: os.environ["COGNITE_OID_ACCESS_TOKEN"]),
            client_name="cepio-oid-m0-readonly",
        )
    if auth == "interactive":
        return CogniteClient.default_oauth_interactive(
            project=project,
            cdf_cluster="api",
            tenant_id=OID_TENANT,
            client_id=OID_CLIENT_ID,
            client_name="cepio-oid-m0-readonly",
        )
    raise ValueError("Unknown authentication mode")


def write_private_json(path: Path, report: dict) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic mode 0600 output: no accidental publication to a repository or stdout.
    fd, tmp = tempfile.mkstemp(prefix=".oid-m0-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Cognite OID M0 inventory")
    parser.add_argument("--project", choices=sorted(OID_PROJECTS), default="publicdata")
    parser.add_argument("--auth", choices=("interactive", "env"), default="interactive")
    parser.add_argument("--limit", type=int, default=100, help="Maximum resources per sample (max 200)")
    parser.add_argument("--focus", default="compressor", help="Asset-name search (read-only)")
    parser.add_argument("--focus-limit", type=int, default=20, help="Maximum asset search hits (max 100)")
    parser.add_argument(
        "--output", type=Path, default=Path.home() / "cepio-oid-m0-inventory.json"
    )
    args = parser.parse_args(argv)

    try:
        client = build_client(args.project, auth=args.auth)
        report = run_oid_m0_inventory(
            CogniteOIDSDKReader(client),
            limit=args.limit,
            focus_phrase=args.focus,
            focus_limit=args.focus_limit,
        )
        write_private_json(args.output, report)
    except Exception as exc:
        # Do not print Cognite SDK exception bodies: may include upstream response details.
        print(f"M0 blocked: {type(exc).__name__}. Check local credentials, permissions and limits.", file=sys.stderr)
        return 2

    check = report["binding_qualification"]["live_source_conformance"]["status"]
    print(f"M0 snapshot: {args.output.expanduser()}")
    print(f"Project: {report['project']} (read-only; capped per-resource inventory)")
    print(f"Binding conformance: {check} (no host registration or production deployment)")
    print(f"Snapshot SHA-256: {report['snapshot_sha256']}")
    return 0 if check == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
