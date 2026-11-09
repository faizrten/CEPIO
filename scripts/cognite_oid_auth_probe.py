"""Secret-safe Cognite OID connectivity probe for a trusted GitHub Actions runner.

Only GET /assets?limit=1 on publicdata. No raw industrial data, source mutation,
Cognite SDK session persistence, files, Azure writes, inference or token logging.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

TOKEN_URL = (
    "https://login.microsoftonline.com/"
    "48d5043c-cf70-4c49-881c-c638f5796997/oauth2/v2.0/token"
)
CDF_URL = "https://api.cognitedata.com/api/v1/projects/publicdata/assets?limit=1"
CLIENT_ID = "1b90ede3-271e-401b-81a0-a4d52bea3273"
SCOPE = "https://api.cognitedata.com/.default"
MAX_REPLY_BYTES = 65536


class ProbeTransport(Protocol):
    def request_json(
        self, method: str, url: str, *, headers: Mapping[str, str],
        form: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, Any] | None]: ...


class NoRedirect(HTTPRedirectHandler):
    """Never allow a secret-bearing probe to follow redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPSProbeTransport:
    def __init__(self) -> None:
        self.opener = build_opener(
            ProxyHandler({}),
            NoRedirect(),
            HTTPSHandler(context=ssl.create_default_context()),
        )

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        form: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, Any] | None]:
        allowed = (
            (method == "POST" and url == TOKEN_URL and form is not None)
            or (method == "GET" and url == CDF_URL and form is None)
        )
        if not allowed:
            raise ValueError("Probe only permits the configured OID OAuth and read-only assets endpoints")
        data = urlencode(form).encode("ascii") if form is not None else None
        req = Request(url, data=data, headers=dict(headers), method=method)
        try:
            with self.opener.open(req, timeout=12) as response:
                status = int(response.status)
                raw = response.read(MAX_REPLY_BYTES + 1)
        except HTTPError as exc:
            # Never inspect or print upstream error bodies/headers: they can carry
            # identity information, request details and auth diagnostics.
            status = int(exc.code)
            exc.close()
            return status, None
        if len(raw) > MAX_REPLY_BYTES:
            return status, None
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, ValueError):
            return status, None
        return status, parsed if isinstance(parsed, dict) else None


def _asset_read(
    transport: ProbeTransport, *, headers: Mapping[str, str]
) -> tuple[int, bool, int]:
    status, body = transport.request_json(
        "GET", CDF_URL, headers={"Accept": "application/json", **headers}
    )
    valid = (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("items"), list)
        and len(body["items"]) <= 1
    )
    count = len(body["items"]) if valid and body is not None else 0
    return status, valid, count


def probe_oid_credential(secret: str, transport: ProbeTransport) -> dict[str, object]:
    """Attempt supported OIDC secret flow, then explicitly bounded legacy API-key read.

    A successful OAuth token is NEVER reused as a legacy API key. A CDF 403 after
    OAuth success is a project-authorization failure, not a reason to retry keys.
    """
    if not secret.strip() or "\n" in secret or "\r" in secret:
        return {"status": "blocked", "reason": "missing-or-invalid-secret"}
    common = {"project": "publicdata", "access": "read-only", "sample_limit": 1}
    oauth_status, payload = transport.request_json(
        "POST",
        TOKEN_URL,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        form={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": secret,
            "scope": SCOPE,
        },
    )
    if oauth_status == 200:
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            return {**common, "status": "blocked", "reason": "invalid-oauth-response"}
        code, valid, count = _asset_read(
            transport, headers={"Authorization": f"Bearer {token}"}
        )
        if valid:
            return {
                **common,
                "status": "passed",
                "auth_method": "oidc-client-credentials",
                "assets_sampled": count,
            }
        return {
            **common,
            "status": "blocked",
            "reason": "cdf-read-rejected-or-malformed",
            "oauth_token_grant": "passed",
            "cdf_http_status": code,
        }

    if oauth_status not in (400, 401, 403):
        return {
            **common,
            "status": "blocked",
            "reason": "oauth-service-unavailable-or-unexpected",
            "oauth_http_status": oauth_status,
        }
    code, valid, count = _asset_read(transport, headers={"api-key": secret})
    if valid:
        return {
            **common,
            "status": "passed",
            "auth_method": "legacy-api-key",
            "assets_sampled": count,
            "migration": "legacy-api-keys-are-deprecated-use-oidc",
        }
    return {
        **common,
        "status": "blocked",
        "reason": "oidc-and-legacy-auth-rejected-or-malformed",
        "oauth_http_status": oauth_status,
        "legacy_cdf_http_status": code,
    }


def main() -> int:
    secret = os.environ.get("OID_API", "")
    if not secret:
        print(json.dumps({"status": "blocked", "reason": "OID_API-secret-not-visible-to-job"}))
        return 2
    try:
        report = probe_oid_credential(secret, HTTPSProbeTransport())
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        # Exception bodies can contain sensitive upstream details; print only class.
        report = {"status": "blocked", "reason": "transport-or-config", "error_type": type(exc).__name__}
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
