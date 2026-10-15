from __future__ import annotations

import re
from pathlib import Path

import yaml

from cepio.sdk import API_OPERATIONS


ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi" / "cepio-v1.yaml"
TYPESCRIPT = ROOT / "clients" / "typescript" / "cepio.ts"
TS_OPERATION = re.compile(
    r'^\s*(\w+): \["(GET|POST|PUT|PATCH|DELETE)", "([^"]+)"\] as const,\s*$'
)


def openapi_operations() -> dict[str, tuple[str, str]]:
    schema = yaml.safe_load(OPENAPI.read_text())
    result: dict[str, tuple[str, str]] = {}
    for path, item in schema.get("paths", {}).items():
        for method, operation in item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation_id = operation.get("operationId")
            if not operation_id:
                raise SystemExit(f"OpenAPI operation missing operationId: {method.upper()} {path}")
            result[operation_id] = (method.upper(), path)
    return result


def typescript_operations() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for line in TYPESCRIPT.read_text().splitlines():
        match = TS_OPERATION.match(line)
        if match:
            operation_id, method, path = match.groups()
            result[operation_id] = (method, path)
    return result


def describe_diff(name: str, expected: dict, actual: dict) -> list[str]:
    messages: list[str] = []
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(
        key for key in set(expected).intersection(actual) if expected[key] != actual[key]
    )
    if missing:
        messages.append(f"{name} missing operations: {missing}")
    if extra:
        messages.append(f"{name} has extra operations: {extra}")
    for key in changed:
        messages.append(
            f"{name} mismatch for {key}: expected {expected[key]!r}, got {actual[key]!r}"
        )
    return messages


def main() -> int:
    expected = openapi_operations()
    errors = []
    errors.extend(describe_diff("Python client", expected, API_OPERATIONS))
    errors.extend(describe_diff("TypeScript client", expected, typescript_operations()))
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"CEPIO clients match OpenAPI v1 route contract: {len(expected)} operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
