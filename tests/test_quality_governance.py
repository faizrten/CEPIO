"""Negative controls ensure the new gates detect representative regressions."""

import importlib.util
from pathlib import Path


def load_script(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openapi_schema_regressions_are_detected():
    compare = load_script("check_compatibility_evidence").removed_contract
    old = {"schema": {"type": "string", "enum": ["a", "b"]}}
    assert compare(old, {"schema": {"type": "integer"}})
    assert not compare(old, {**old, "new": {}})


def test_public_signature_and_persistence_changes_are_detected():
    module = load_script("check_compatibility_evidence")
    assert module.python_contract("def query(limit=1): pass") != module.python_contract(
        "def query(limit): pass"
    )
    assert module.ddl('sql = "CREATE TABLE objects (id TEXT);"')
    assert module.ddl('sql = "CREATE TABLE objects (id TEXT);"') != module.ddl(
        'sql = "CREATE TABLE objects (id INT);"'
    )
