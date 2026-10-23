"""Read-only OIDC diagnostics; never log tokens, raw claims or response bodies."""

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request


KNOWN_ROLES = {"cepio_management_reader", "cepio_admin", "ai_agent_recommender"}
KNOWN_ERRORS = {
    "authentication_required",
    "invalid_token",
    "mcp_role_required",
    "management_forbidden",
    "mcp_not_ready",
}
GUID = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")


def az_read(*args):
    result = subprocess.run(
        ["az", *args, "--output", "json", "--only-show-errors"],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode:
        raise RuntimeError("AZURE_READ_OR_TOKEN_DENIED")
    return json.loads(result.stdout)


def decode_diagnostic_claims(token):
    # Diagnostic comparison only; authorization remains the live API's decision.
    parts = token.split(".")
    if len(parts) != 3 or len(token) > 65536:
        raise ValueError("TOKEN_DIAGNOSTICS_UNAVAILABLE")
    claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    if not isinstance(claims, dict):
        raise ValueError("TOKEN_DIAGNOSTICS_UNAVAILABLE")
    return claims


def identity_diagnostics(claims, settings, client_id, tenant_id):
    roles = claims.get("roles", [])
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        roles = []
    effective = set(roles)
    mapping = json.loads(settings.get("CEPIO_GROUP_ROLE_MAP", "{}"))
    if not isinstance(mapping, dict):
        raise ValueError("INVALID_GROUP_ROLE_MAP")
    for group in claims.get("groups", []):
        mapped = mapping.get(group, [])
        if isinstance(mapped, list):
            effective.update(role for role in mapped if isinstance(role, str))
    tenant = settings.get("CEPIO_ENTRA_TENANT_ID", "")
    issuer = (
        settings.get("CEPIO_ENTRA_ISSUER") or f"https://login.microsoftonline.com/{tenant}/v2.0"
    )
    return {
        "diagnostic_claims_only_not_signature_proof": True,
        "audience_matches_config": claims.get("aud") == settings["CEPIO_ENTRA_AUDIENCE"],
        "tenant_matches_config": bool(tenant) and claims.get("tid") == tenant,
        "tenant_matches_oidc": claims.get("tid") == tenant_id,
        "client_matches_oidc": (claims.get("azp") or claims.get("appid")) == client_id,
        "issuer_matches_config": claims.get("iss") == issuer,
        "token_role_count": len(roles),
        "effective_role_count": len(effective),
        "known_effective_roles": sorted(effective & KNOWN_ROLES),
        "unknown_effective_role_count": len(effective - KNOWN_ROLES),
    }


def safe_rejection(body):
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        return "unclassified"
    if not isinstance(payload, dict):
        return "unclassified"
    detail = payload.get("detail", payload)
    code = detail.get("code") if isinstance(detail, dict) else None
    if isinstance(code, str) and code in KNOWN_ERRORS:
        return code
    error = payload.get("error")
    if isinstance(error, dict) and type(error.get("code")) is int:
        code = error["code"]
        if code in {-32700, -32600, -32601, -32602, -32603, -32000}:
            return f"jsonrpc_{code}"
    return "unclassified"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(opener, host, path, token, payload=None, protocol=None):
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if protocol:
        headers["MCP-Protocol-Version"] = protocol
    request = urllib.request.Request(
        "https://" + host + path,
        headers=headers,
        data=json.dumps(payload).encode() if payload else None,
    )
    try:
        with opener.open(request, timeout=30) as response:
            status, body = response.status, response.read(262144)
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read(65536)
        error.close()
    except (urllib.error.URLError, TimeoutError):
        return {"http_status": 0, "error_code": "transport_failed"}, None
    diagnostic = {"http_status": status, "error_code": safe_rejection(body)}
    if status != 200:
        return diagnostic, None
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        diagnostic["error_code"] = "non_json_response"
        return diagnostic, None
    return diagnostic, data


def graph_role_diagnostics(claims):
    """Attempt existing Graph read access only; never request/grant permissions."""
    principal, audience = claims.get("oid", ""), claims.get("aud", "")
    app_id = audience.removeprefix("api://") if isinstance(audience, str) else ""
    if (
        not isinstance(principal, str)
        or not GUID.fullmatch(principal)
        or not GUID.fullmatch(app_id)
    ):
        return {"graph_assignments": "unavailable_identifier_shape"}
    try:
        apps = az_read(
            "rest",
            "--method",
            "GET",
            "--url",
            "https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '"
            + app_id
            + "'&$select=id,appRoles",
        )
        values = apps.get("value", [])
        if len(values) != 1:
            return {"graph_assignments": "api_principal_not_unique"}
        api = values[0]
        assignments = az_read(
            "rest",
            "--method",
            "GET",
            "--url",
            "https://graph.microsoft.com/v1.0/servicePrincipals/"
            + principal
            + "/appRoleAssignments?$select=appRoleId,resourceId",
        )
        if assignments.get("@odata.nextLink"):
            return {"graph_assignments": "incomplete_pagination"}
        assigned = {
            row.get("appRoleId")
            for row in assignments.get("value", [])
            if row.get("resourceId") == api["id"]
        }
        known = sorted(
            role["value"]
            for role in api.get("appRoles", [])
            if role.get("id") in assigned and role.get("value") in KNOWN_ROLES
        )
        return {
            "graph_assignments": "read",
            "api_assignment_count": len(assigned),
            "known_assigned_roles": known,
        }
    except (RuntimeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return {"graph_assignments": "read_unavailable_no_permissions_changed"}


def main():
    group, app = os.environ["RESOURCE_GROUP"], os.environ["APP_NAME"]
    if app != "cepio-demo-31d48" or not group:
        raise SystemExit("UNEXPECTED_TARGET")
    host = az_read(
        "webapp", "show", "--resource-group", group, "--name", app, "--query", "defaultHostName"
    )
    if host != "cepio-demo-31d48.azurewebsites.net":
        raise SystemExit("UNEXPECTED_HOST")
    names = {
        "CEPIO_ENTRA_AUDIENCE",
        "CEPIO_ENTRA_TENANT_ID",
        "CEPIO_ENTRA_ISSUER",
        "CEPIO_GROUP_ROLE_MAP",
    }
    query = "[?" + " || ".join("name=='" + name + "'" for name in sorted(names)) + "]"
    settings = {
        row["name"]: row["value"]
        for row in az_read(
            "webapp",
            "config",
            "appsettings",
            "list",
            "--resource-group",
            group,
            "--name",
            app,
            "--query",
            query,
        )
        if row["name"] in names
    }
    audience = settings.get("CEPIO_ENTRA_AUDIENCE", "")
    if not isinstance(audience, str) or not audience:
        raise SystemExit("CEPIO_AUDIENCE_MISSING")
    resource = "api://" + audience if GUID.fullmatch(audience) else audience
    token = az_read("account", "get-access-token", "--resource", resource, "--query", "accessToken")
    claims = decode_diagnostic_claims(token)
    results = {
        "identity": identity_diagnostics(
            claims, settings, os.environ["OIDC_CLIENT_ID"], os.environ["OIDC_TENANT_ID"]
        )
    }
    opener = urllib.request.build_opener(NoRedirect())
    for name, path in [("rest", "/api/v1/objects"), ("management", "/management/v1/health")]:
        results[name], _ = request_json(opener, host, path, token)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "cepio-readonly-proof", "version": "1"},
        },
    }
    results["mcp_initialize"], initialized = request_json(opener, host, "/mcp", token, payload)
    initialized_result = initialized.get("result") if isinstance(initialized, dict) else None
    version = (
        initialized_result.get("protocolVersion") if isinstance(initialized_result, dict) else None
    )
    results["mcp_tools_list"] = {"http_status": 0, "error_code": "skipped_initialize_failed"}
    listed = None
    if isinstance(version, str) and version in {"2025-03-26", "2025-06-18", "2025-11-25"}:
        payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        results["mcp_tools_list"], listed = request_json(
            opener, host, "/mcp", token, payload, version
        )
    results["directory"] = graph_role_diagnostics(claims)
    results["qualified"] = all(
        results[name]["http_status"] == 200
        for name in ("rest", "management", "mcp_initialize", "mcp_tools_list")
    ) and bool(
        isinstance(listed, dict)
        and isinstance(listed.get("result"), dict)
        and isinstance(listed["result"].get("tools"), list)
        and listed["result"].get("tools")
    )
    # Only this constructed allowlisted diagnostic object is ever written.
    report = json.dumps(results, sort_keys=True)
    print("READONLY_OIDC_DIAGNOSTICS " + report)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write("## Read-only OIDC diagnostics\n\n```json\n" + report + "\n```\n")
        summary.write(
            "No tokens, raw claims, identifiers or response bodies logged; no grants, tools or inference.\n"
        )
    if not results["qualified"]:
        raise SystemExit("AUTHENTICATED_ACCESS_NOT_QUALIFIED")


if __name__ == "__main__":
    main()
