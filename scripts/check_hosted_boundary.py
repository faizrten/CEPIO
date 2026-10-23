"""Bounded, read-only hosted protocol checks. Never invoke tools or models."""

import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_startup(config):
    command = (config.get("appCommandLine") or "").strip()
    if command == "":
        return "image-default"
    if command == "uvicorn cepio.host_api:app --host 0.0.0.0 --port 8000":
        return "host-api-override"
    # Unknown overrides can contain secrets; never print the raw command.
    raise ValueError("Unexpected App Service startup override; inspect privately")


def request_status(opener, base_url, path, timeout):
    request = urllib.request.Request(
        base_url + path,
        data=b"{}" if path == "/mcp" else None,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
            headers = response.headers
            body = response.read(65536) if path == "/api/v1/health" else b""
    except urllib.error.HTTPError as error:
        status, headers, body = error.code, error.headers, b""
        error.close()
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, False
    if path == "/api/v1/health":
        try:
            return status, status == 200 and json.loads(body).get("status") == "ok"
        except (ValueError, AttributeError):
            return status, False
    return status, status == 401 and headers.get("WWW-Authenticate", "").lower() == "bearer"


def wait_for_boundary(
    base_url,
    *,
    timeout=180,
    interval=5,
    stable_rounds=3,
    probe=None,
    clock=time.monotonic,
    sleep=time.sleep,
):
    parsed = urllib.parse.urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Expected an HTTPS origin without credentials, path or query")
    if timeout <= 0 or interval <= 0 or stable_rounds < 1:
        raise ValueError("Positive timeout, interval and stable rounds required")
    opener = urllib.request.build_opener(NoRedirect())
    if probe is None:

        def probe(path, budget):
            return request_status(opener, base_url.rstrip("/"), path, budget)

    deadline, stable = clock() + timeout, 0
    paths = ("/api/v1/health", "/api/v1/objects", "/management/v1/health", "/mcp")
    while clock() < deadline:
        results = {}
        for path in paths:
            remaining = deadline - clock()
            if remaining <= 0:
                raise TimeoutError("Hosted boundary did not stabilize before deadline")
            status, passed = probe(path, min(10, remaining))
            results[path] = passed
            print(f"{path}: HTTP {status}; {'PASS' if passed else 'WAIT'}", flush=True)
            if path != "/api/v1/health" and 200 <= status < 300:
                raise RuntimeError("Anonymous protected access succeeded; stop deployment")
        stable = stable + 1 if all(results.values()) else 0
        if stable >= stable_rounds:
            return
        remaining = deadline - clock()
        if remaining > 0:
            sleep(min(interval, remaining))
    raise TimeoutError("Hosted boundary did not stabilize before deadline")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--startup-config", type=Path)
    args = parser.parse_args()
    if not args.base_url and not args.startup_config:
        parser.error("Provide --base-url or --startup-config")
    if args.startup_config:
        config = json.loads(args.startup_config.read_text(encoding="utf-8"))
        print("App Service startup: " + validate_startup(config))
    if args.base_url:
        wait_for_boundary(args.base_url)
        print("Hosted REST, Management and MCP anonymous boundary: PASS")


if __name__ == "__main__":
    main()
