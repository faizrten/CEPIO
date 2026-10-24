"""Compare complete generated HTTP contracts with an immutable git base, offline."""

from __future__ import annotations

import argparse
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
EXPORT = """
import json, sys
from fastapi.openapi.utils import get_openapi
surface = sys.argv[1]
if surface == 'application':
    from cepio.public_api import app
    routes = [r for r in app.routes if getattr(r, 'path', '').startswith('/api/v1/')]
elif surface == 'management':
    from cepio import api
    from cepio.management_remote import build_remote_management_router
    from cepio.management_runtime import build_management_service
    routes = build_remote_management_router(build_management_service(api.runtime)).routes
elif surface == 'labs':
    from service.app import app
    routes = [r for r in app.routes if getattr(r, 'path', '').startswith('/labs/v1/')]
else:
    raise ValueError('Unknown HTTP surface')
print(json.dumps(get_openapi(title=surface, version='v1', routes=routes), sort_keys=True))
"""


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, timeout=180, **kwargs)


def export(root: Path, surface: str) -> dict:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CEPIO_", "LABS_", "STUDIO_", "AUTH_", "AZURE_", "IDENTITY_"))
    }
    env.update(
        CEPIO_ENVIRONMENT="test",
        CEPIO_DB_URL="memory://",
        CEPIO_AUTH_MODE="entra",
        PYTHONPATH=os.pathsep.join([str(root / "src"), str(root)]),
    )
    result = run([sys.executable, "-c", EXPORT, surface], cwd=root, env=env, text=True)
    schema = json.loads(result.stdout)
    if not schema.get("paths") or not schema.get("components", {}).get("schemas"):
        raise ValueError("Incomplete generated contract")

    def local_refs(value):
        if isinstance(value, dict):
            if "$ref" in value and not value["$ref"].startswith("#/"):
                raise ValueError("Remote schema references are prohibited")
            for item in value.values():
                local_refs(item)
        elif isinstance(value, list):
            for item in value:
                local_refs(item)

    local_refs(schema)
    return schema


def operations(schema):
    return {
        (path, method): operation
        for path, item in schema["paths"].items()
        for method, operation in item.items()
        if method in METHODS
    }


def security_changes(before, after):
    """Compatibility alone must not permit a newly anonymous API or weaker scheme."""
    errors = []
    if before.get("components", {}).get("securitySchemes", {}) != after.get("components", {}).get(
        "securitySchemes", {}
    ):
        errors.append("Security scheme definitions changed")
    new = operations(after)
    for key, operation in operations(before).items():
        if key not in new:
            continue  # The semantic comparator rejects operation removal.
        effective = operation.get("security", before.get("security", []))
        revised = new[key].get("security", after.get("security", []))
        if effective != revised:
            errors.append(f"{key}: authentication requirement changed")
        if operation.get("operationId") != new[key].get("operationId"):
            errors.append(f"{key}: operation ID changed")

        # Custom assertion authentication can be declared as an Authorization header.
        def headers(op):
            return [
                p
                for p in op.get("parameters", [])
                if p.get("in") == "header" and p.get("name", "").lower() == "authorization"
            ]

        if headers(operation) != headers(new[key]):
            errors.append(f"{key}: authorization header contract changed")
    return errors


def compare(binary, before, after, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    for name, schema in [("base", before), ("head", after)]:
        (output / f"{name}.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run(
        [
            binary,
            "breaking",
            "--fail-on",
            "WARN",
            "--format",
            "json",
            "--",
            str(output / "base.json"),
            str(output / "head.json"),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    (output / "breaking.json").write_text(result.stdout, encoding="utf-8")
    (output / "comparator.stderr.txt").write_text(result.stderr, encoding="utf-8")
    # A valid report is mandatory, including for the no-findings case.
    json.loads(result.stdout)
    failures = security_changes(before, after)
    (output / "security.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    return result.returncode == 0 and not failures


def self_test(binary, output):
    schema = {
        "openapi": "3.1.0",
        "info": {"title": "Synthetic", "version": "1"},
        "paths": {
            "/items": {
                "post": {
                    "operationId": "createItem",
                    "security": [{"bearer": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "limit": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id"],
                                        "properties": {"id": {"type": "string"}},
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
    }
    variants = {"identical": (deepcopy(schema), True)}
    additive = deepcopy(schema)
    additive["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"][
        "properties"
    ]["note"] = {"type": "string"}
    variants["optional-request-field"] = additive, True
    required = deepcopy(schema)
    required["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"][
        "required"
    ] = ["name"]
    variants["new-required-input"] = required, False
    constrained = deepcopy(schema)
    constrained["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"][
        "properties"
    ]["limit"]["maximum"] = 5
    variants["tightened-bound"] = constrained, False
    response = deepcopy(schema)
    response["paths"]["/items"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] = {"type": "object"}
    variants["lost-response-guarantee"] = response, False
    anonymous = deepcopy(schema)
    anonymous["paths"]["/items"]["post"]["security"] = []
    variants["removed-authentication"] = anonymous, False
    renamed = deepcopy(schema)
    renamed["paths"]["/items"]["post"]["operationId"] = "renamed"
    variants["changed-operation-id"] = renamed, False
    for name, (revision, expected) in variants.items():
        if compare(binary, schema, revision, output / name) != expected:
            raise ValueError(f"Comparator negative/positive control failed: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument(
        "--surfaces", nargs="+", choices=["application", "management", "labs"], required=True
    )
    parser.add_argument("--oasdiff", default="oasdiff")
    parser.add_argument("--out", default="evidence/openapi")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    base = run(["git", "rev-parse", "--verify", args.base + "^{commit}"], text=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("Invalid baseline commit")
    output = Path(args.out).resolve()
    self_test(args.oasdiff, output / "controls")
    archive = run(["git", "archive", "--format=tar", base]).stdout
    results = {}
    with tempfile.TemporaryDirectory(prefix="api-contract-base-") as directory:
        source = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(source, filter="data")
        for surface in args.surfaces:
            results[surface] = compare(
                args.oasdiff, export(source, surface), export(root, surface), output / surface
            )
    report = {
        "base": base,
        "surfaces": results,
        "compatible": all(results.values()),
        "limits": "Declared HTTP contract only; runtime authorization and deployed qualification remain separate.",
    }
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return int(not report["compatible"])


if __name__ == "__main__":
    raise SystemExit(main())
