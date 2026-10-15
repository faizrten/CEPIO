from __future__ import annotations

from pathlib import Path
import sys

import yaml

from cepio.public_api import app


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def route_signature(schema: dict) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            method_lower = method.lower()
            if method_lower not in HTTP_METHODS:
                continue
            result[(path, method_lower)] = operation.get("operationId", "")
    return result


def main() -> int:
    baseline_path = Path("openapi/cepio-v1.yaml")
    baseline = yaml.safe_load(baseline_path.read_text()) or {}
    generated = app.openapi()

    generated_paths = set(generated.get("paths", {}))
    unversioned = sorted(path for path in generated_paths if not path.startswith("/api/v1/"))
    if unversioned:
        print("Public OpenAPI unexpectedly exposes unversioned paths:")
        for path in unversioned:
            print(f"  - {path}")
        return 1

    expected = route_signature(baseline)
    actual = route_signature(generated)

    missing = sorted(set(expected) - set(actual))
    additional = sorted(set(actual) - set(expected))
    changed = sorted(
        (route, expected[route], actual[route])
        for route in set(expected).intersection(actual)
        if expected[route] != actual[route]
    )

    if missing or additional or changed:
        if missing:
            print("Missing public API operations:")
            for path, method in missing:
                print(f"  - {method.upper()} {path} ({expected[(path, method)]})")
        if additional:
            print("New public API operations not present in the accepted baseline:")
            for path, method in additional:
                print(f"  - {method.upper()} {path} ({actual[(path, method)]})")
        if changed:
            print("Changed operation IDs:")
            for (path, method), before, after in changed:
                print(f"  - {method.upper()} {path}: {before} -> {after}")
        print("Update openapi/cepio-v1.yaml only after an intentional API-contract review.")
        return 1

    print(f"CEPIO API v1 contract OK: {len(actual)} operations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
