"""Credential-isolated Cognite OID probe regression tests; no network or secret access."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cognite_oid_auth_probe import (  # noqa: E402
    CDF_URL,
    CLIENT_ID,
    NoRedirect,
    SCOPE,
    TOKEN_URL,
    HTTPSProbeTransport,
    probe_oid_credential,
)


class ProbeFake:
    def __init__(
        self,
        *,
        oauth_status: int = 200,
        oauth_json: dict | None = None,
        cdf_status: int = 200,
        cdf_json: dict | None = None,
    ):
        self.oauth_status = oauth_status
        self.oauth_json = (
            {"access_token": "fake-token"} if oauth_json is None else oauth_json
        )
        self.cdf_status = cdf_status
        self.cdf_json = {"items": [{"id": 123}]} if cdf_json is None else cdf_json
        self.calls = []

    def request_json(self, method, url, *, headers, form=None):
        self.calls.append((method, url, dict(headers), dict(form or {})))
        if method == "POST":
            assert url == TOKEN_URL
            assert form["client_id"] == CLIENT_ID
            assert form["scope"] == SCOPE
            assert form["grant_type"] == "client_credentials"
            return self.oauth_status, self.oauth_json if self.oauth_status == 200 else None
        assert method == "GET"
        assert url == CDF_URL
        assert form is None
        return self.cdf_status, self.cdf_json if self.cdf_status == 200 else None


def test_valid_oid_client_secret_performs_only_one_bounded_read():
    stub = ProbeFake()
    report = probe_oid_credential("test-secret", stub)
    assert report == {
        "project": "publicdata",
        "access": "read-only",
        "sample_limit": 1,
        "status": "passed",
        "auth_method": "oidc-client-credentials",
        "assets_sampled": 1,
    }
    assert [item[0] for item in stub.calls] == ["POST", "GET"]
    assert stub.calls[1][2]["Authorization"] == "Bearer fake-token"
    assert "test-secret" not in repr(report)
    assert "fake-token" not in repr(report)


def test_legacy_api_key_fallback_only_after_oidc_credential_rejected():
    stub = ProbeFake(oauth_status=401)
    report = probe_oid_credential("test-legacy-key", stub)
    assert report["status"] == "passed"
    assert report["auth_method"] == "legacy-api-key"
    assert report["migration"].startswith("legacy-api-keys")
    assert stub.calls[-1][2]["api-key"] == "test-legacy-key"
    assert "test-legacy-key" not in repr(report)


def test_oauth_success_but_cdf_denial_does_not_retry_secret_as_api_key():
    stub = ProbeFake(cdf_status=403)
    report = probe_oid_credential("test-secret", stub)
    assert report["status"] == "blocked"
    assert report["reason"] == "cdf-read-rejected-or-malformed"
    assert report["oauth_token_grant"] == "passed"
    assert report["cdf_http_status"] == 403
    assert len(stub.calls) == 2
    assert not any("api-key" in call[2] for call in stub.calls)


@pytest.mark.parametrize("oauth_status", [302, 429, 500, 503])
def test_oauth_transient_or_redirect_fails_closed(oauth_status):
    stub = ProbeFake(oauth_status=oauth_status)
    report = probe_oid_credential("test-secret", stub)
    assert report["status"] == "blocked"
    assert report["oauth_http_status"] == oauth_status
    assert len(stub.calls) == 1


def test_legacy_denial_records_codes_without_exposing_secret():
    stub = ProbeFake(oauth_status=400, cdf_status=401)
    report = probe_oid_credential("test-secret", stub)
    assert report["status"] == "blocked"
    assert report["oauth_http_status"] == 400
    assert report["legacy_cdf_http_status"] == 401
    assert "test-secret" not in repr(report)


def test_missing_secret_rejected_before_any_request():
    stub = ProbeFake()
    for secret in ("", "   ", "test\nsecret", "test\rsecret"):
        result = probe_oid_credential(secret, stub)
        assert result["reason"] == "missing-or-invalid-secret"
    assert stub.calls == []


@pytest.mark.parametrize("reply", [{}, {"access_token": ""}, {"access_token": 123}])
def test_malformed_oauth_200_never_falls_back_to_key_auth(reply):
    stub = ProbeFake(oauth_json=reply)
    result = probe_oid_credential("test-secret", stub)
    assert result["reason"] == "invalid-oauth-response"
    assert len(stub.calls) == 1


def test_bogus_cdf_success_is_not_accepted():
    stub = ProbeFake(cdf_status=200, cdf_json={"items": "not-a-list"})
    assert probe_oid_credential("test-secret", stub)["status"] == "blocked"
    stub = ProbeFake(cdf_status=200, cdf_json={"items": [{}, {}]})
    assert probe_oid_credential("test-secret", stub)["status"] == "blocked"


def test_transport_permits_only_two_fixed_endpoints_and_no_redirect():
    transport = HTTPSProbeTransport()
    assert NoRedirect().redirect_request(None, None, 302, "", {}, "https://attacker") is None
    with pytest.raises(ValueError, match="only permits"):
        transport.request_json(
            "POST",
            "https://example.com/token",
            headers={},
            form={"client_secret": "test"},
        )
    with pytest.raises(ValueError, match="only permits"):
        transport.request_json(
            "POST",
            CDF_URL,
            headers={"api-key": "test"},
            form={"command": "delete"},
        )


def test_workflow_uses_only_repository_secret_on_trusted_main():
    wf = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/cognite-oid-auth-probe.yml"
    ).read_text()
    assert "secrets.OID_API" in wf
    assert "branches: [main]" in wf
    assert "github.ref == 'refs/heads/main'" in wf
    assert "pull_request_target" not in wf
    assert "pull_request:" not in wf
    assert "upload-artifact" not in wf
    assert "python -I scripts/cognite_oid_auth_probe.py" in wf
