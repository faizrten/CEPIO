import importlib.util
import json
from pathlib import Path
import urllib.error

import pytest


SPEC = importlib.util.spec_from_file_location(
    "auth_probe", Path(__file__).resolve().parents[1] / "scripts/check_authenticated_host.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_identity_comparisons_are_diagnostics_not_authority_and_hide_identifiers():
    claims = {
        "aud": "private-audience",
        "tid": "private-tenant",
        "azp": "private-client",
        "iss": "https://login.microsoftonline.com/private-tenant/v2.0",
        "roles": ["private-role", "cepio_management_reader"],
        "groups": ["private-group"],
    }
    settings = {
        "CEPIO_ENTRA_AUDIENCE": "private-audience",
        "CEPIO_ENTRA_TENANT_ID": "private-tenant",
    }
    result = probe.identity_diagnostics(claims, settings, "private-client", "private-tenant")
    assert result["audience_matches_config"] and result["client_matches_oidc"]
    assert result["tenant_matches_config"] and result["issuer_matches_config"]
    assert result["known_effective_roles"] == ["cepio_management_reader"]
    assert result["unknown_effective_role_count"] == 1
    assert "private-" not in json.dumps(result)
    result = probe.identity_diagnostics({**claims, "aud": "wrong"}, settings, "wrong", "wrong")
    assert not result["audience_matches_config"] and not result["client_matches_oidc"]


def test_roleless_token_and_configured_group_mapping_are_distinguished():
    settings = {
        "CEPIO_ENTRA_AUDIENCE": "api",
        "CEPIO_GROUP_ROLE_MAP": json.dumps({"private-group": ["cepio_management_reader"]}),
    }
    empty = probe.identity_diagnostics({}, settings, "client", "tenant")
    assert empty["effective_role_count"] == 0
    mapped = probe.identity_diagnostics({"groups": ["private-group"]}, settings, "client", "tenant")
    assert mapped["token_role_count"] == 0
    assert mapped["known_effective_roles"] == ["cepio_management_reader"]


@pytest.mark.parametrize(
    "body,expected",
    [
        (b'{"detail":{"code":"mcp_role_required","message":"SECRET"}}', "mcp_role_required"),
        (b'{"detail":{"code":"management_forbidden"}}', "management_forbidden"),
        (b'{"detail":{"code":"SECRET"}}', "unclassified"),
        (b'{"error":{"code":-32600,"data":"SECRET"}}', "jsonrpc_-32600"),
        (b'{"error":{"code":"SECRET"}}', "unclassified"),
        (b"<html>SECRET</html>", "unclassified"),
        (b"[]", "unclassified"),
    ],
)
def test_rejection_never_echoes_raw_body_or_arbitrary_codes(body, expected):
    assert probe.safe_rejection(body) == expected


def test_http_403_preserves_exact_allowlisted_mcp_code_without_body():
    import io

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "https://example.test/mcp"
            raise urllib.error.HTTPError(
                request.full_url,
                403,
                "SECRET",
                {},
                io.BytesIO(b'{"detail":{"code":"mcp_role_required","message":"SECRET"}}'),
            )

    result, payload = probe.request_json(
        Opener(), "example.test", "/mcp", "SECRET", {"method": "initialize"}
    )
    assert result == {"http_status": 403, "error_code": "mcp_role_required"}
    assert payload is None
    assert "SECRET" not in json.dumps(result)


def test_unavailable_graph_reads_do_not_request_permission_changes(monkeypatch):
    calls = []

    def az(*args):
        calls.append(args)
        raise RuntimeError("SECRET")

    monkeypatch.setattr(probe, "az_read", az)
    result = probe.graph_role_diagnostics(
        {
            "oid": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "aud": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        }
    )
    assert result == {"graph_assignments": "read_unavailable_no_permissions_changed"}
    assert len(calls) == 1 and calls[0][:3] == ("rest", "--method", "GET")


def test_assigned_graph_role_projection_hides_ids_and_unrelated_permissions(monkeypatch):
    responses = iter(
        [
            {
                "value": [
                    {
                        "id": "PRIVATE_API_ID",
                        "appRoles": [{"id": "PRIVATE_ROLE_ID", "value": "cepio_management_reader"}],
                    }
                ]
            },
            {
                "value": [
                    {"resourceId": "PRIVATE_API_ID", "appRoleId": "PRIVATE_ROLE_ID"},
                    {"resourceId": "OTHER_API", "appRoleId": "OTHER_ROLE"},
                ]
            },
        ]
    )
    monkeypatch.setattr(probe, "az_read", lambda *args: next(responses))
    result = probe.graph_role_diagnostics(
        {
            "oid": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "aud": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        }
    )
    assert result["known_assigned_roles"] == ["cepio_management_reader"]
    assert result["api_assignment_count"] == 1
    assert "PRIVATE" not in json.dumps(result) and "OTHER" not in json.dumps(result)


def test_failed_check_still_writes_redacted_summary_and_never_lists_or_calls_tools(
    monkeypatch, tmp_path, capsys
):
    for name, value in {
        "RESOURCE_GROUP": "private-group",
        "APP_NAME": "cepio-demo-31d48",
        "OIDC_CLIENT_ID": "private-client",
        "OIDC_TENANT_ID": "private-tenant",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }.items():
        monkeypatch.setenv(name, value)

    def az(*args):
        if args[:2] == ("webapp", "show"):
            return "cepio-demo-31d48.azurewebsites.net"
        if args[:3] == ("webapp", "config", "appsettings"):
            return [
                {"name": "CEPIO_ENTRA_AUDIENCE", "value": "private-audience"},
                {"name": "CEPIO_ENTRA_TENANT_ID", "value": "private-tenant"},
            ]
        return "SECRET_TOKEN"

    monkeypatch.setattr(probe, "az_read", az)
    monkeypatch.setattr(
        probe,
        "decode_diagnostic_claims",
        lambda token: {"aud": "private-audience", "tid": "private-tenant", "azp": "private-client"},
    )
    calls = []

    def request(opener, host, path, token, payload=None, protocol=None):
        calls.append(payload)
        if path == "/api/v1/objects":
            return {"http_status": 200, "error_code": "unclassified"}, {"private": "SECRET"}
        code = "management_forbidden" if path.startswith("/management") else "mcp_role_required"
        return {"http_status": 403, "error_code": code}, None

    monkeypatch.setattr(probe, "request_json", request)
    with pytest.raises(SystemExit, match="AUTHENTICATED_ACCESS_NOT_QUALIFIED"):
        probe.main()
    output = capsys.readouterr().out
    assert '"mcp_role_required"' in output and '"qualified": false' in output
    assert "SECRET" not in output and "private-" not in output
    assert '"mcp_role_required"' in (tmp_path / "summary").read_text()
    assert [item["method"] for item in calls if item] == ["initialize"]
