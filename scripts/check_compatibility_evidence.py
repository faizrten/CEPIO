"""Compare against the immutable PR base, in addition to accepted-baseline gates."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml

from cepio.compatibility import (
    evaluate_compatibility,
    load_migrations,
    snapshot_from_git_ref,
)
from cepio.modules import ModuleCatalogue
from cepio.public_api import app

ROOT = Path(__file__).resolve().parents[1]


def git_text(base: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{base}:{path}"], check=True, capture_output=True, text=True
    ).stdout


def removed_contract(old, new, path=""):
    """Conservative schema comparison: existing values must remain identical."""
    if isinstance(old, dict) and isinstance(new, dict):
        return [
            item
            for key, value in old.items()
            if key not in {"description", "summary", "example", "examples"}
            for item in (
                [f"{path}/{key}: removed"]
                if key not in new
                else removed_contract(value, new[key], f"{path}/{key}")
            )
        ]
    if old != new:
        return [f"{path}: changed"]
    return []


def python_contract(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    result = {}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                result[alias.asname or alias.name] = ast.dump(node, include_attributes=False)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            result[node.name] = ast.dump(node.args, include_attributes=False)
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            result[node.name] = ",".join(ast.dump(base) for base in node.bases)
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    not member.name.startswith("_") or member.name == "__init__"
                ):
                    result[f"{node.name}.{member.name}"] = ast.dump(
                        member.args, include_attributes=False
                    )
    return result


def ddl(source: str) -> list[str]:
    return sorted(
        re.sub(r"\s+", " ", match).strip()
        for match in re.findall(r"CREATE TABLE[^;]+;", source, re.I)
    )


def generated_base_api(base: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="cepio-api-base-") as directory:
        checkout = str(Path(directory) / "repo")
        subprocess.run(
            ["git", "worktree", "add", "--detach", checkout, base], check=True, capture_output=True
        )
        try:
            environment = dict(os.environ, PYTHONPATH=str(Path(checkout) / "src"))
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import json; from cepio.public_api import app; print(json.dumps(app.openapi()))",
                ],
                cwd=checkout,
                env=environment,
                check=True,
                text=True,
                capture_output=True,
            )
            return json.loads(result.stdout)
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", checkout], check=True, capture_output=True
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", default="evidence/compatibility.json")
    args = parser.parse_args()
    base = subprocess.run(
        ["git", "rev-parse", "--verify", args.base + "^{commit}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    failures = []
    old_api = yaml.safe_load(git_text(base, "openapi/cepio-v1.yaml"))
    new_api = yaml.safe_load((ROOT / "openapi/cepio-v1.yaml").read_text(encoding="utf-8"))
    failures.extend("OpenAPI " + item for item in removed_contract(old_api, new_api))
    failures.extend(
        "Generated OpenAPI " + item
        for item in removed_contract(generated_base_api(base), app.openapi())
    )
    for path in ["src/cepio/__init__.py", "src/cepio/sdk.py"]:
        before = python_contract(git_text(base, path))
        after = python_contract((ROOT / path).read_text(encoding="utf-8"))
        failures.extend(
            f"Python {path}: {name} removed or signature changed"
            for name, signature in before.items()
            if after.get(name) != signature
        )
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", base, "src/cepio"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    for path in tracked:
        if path.endswith(".py"):
            if path not in {"src/cepio/__init__.py", "src/cepio/sdk.py"}:
                before_python = python_contract(git_text(base, path))
                current_path = ROOT / path
                after_python = (
                    python_contract(current_path.read_text(encoding="utf-8"))
                    if current_path.exists()
                    else {}
                )
                failures.extend(
                    f"Python {path}: {name} removed or signature changed"
                    for name, signature in before_python.items()
                    if after_python.get(name) != signature and not name.startswith("_")
                )
            before = ddl(git_text(base, path))
            after_path = ROOT / path
            after = ddl(after_path.read_text(encoding="utf-8")) if after_path.exists() else []
            failures.extend(
                f"Persistence {path}: changed table {item}" for item in before if item not in after
            )
    ontology = evaluate_compatibility(
        snapshot_from_git_ref(ROOT, base),
        ModuleCatalogue.load(ROOT / "ontology-modules.yaml").snapshot(ROOT),
        baseline_ref=base,
        baseline_label="PR base",
        migrations=load_migrations(ROOT / "compatibility/migrations", baseline_ref=base),
    )
    digest = hashlib.sha256(json.dumps(sorted(failures)).encode()).hexdigest()
    declaration_path = ROOT / "compatibility/interface-migrations" / f"{digest}.json"
    declared = False
    if failures and declaration_path.exists():
        declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
        old_version = git_text(base, "src/cepio/_version.py")
        new_version = (ROOT / "src/cepio/_version.py").read_text(encoding="utf-8")
        declared = (
            declaration.get("base") == base
            and bool(declaration.get("rationale"))
            and bool(declaration.get("migration"))
            and old_version != new_version
        )
    report = {
        "base": base,
        "interface_changes": failures,
        "change_digest": digest,
        "migration_declared": declared,
        "ontology": ontology.to_dict(),
        "compatible": ontology.compatible and (not failures or declared),
    }
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(not report["compatible"])


if __name__ == "__main__":
    raise SystemExit(main())
