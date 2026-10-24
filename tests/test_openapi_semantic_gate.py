"""Boundary regressions for semantic comparison and authentication preservation."""

import importlib.util
from pathlib import Path


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/check_openapi_compatibility.py"
    spec = importlib.util.spec_from_file_location("openapi_gate", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_new_anonymous_operation_contract_is_not_considered_security_compatible():
    gate = module()
    before = {"paths": {"/items": {"get": {"operationId": "items", "security": [{"jwt": []}]}}}}
    after = {"paths": {"/items": {"get": {"operationId": "items", "security": []}}}}
    assert gate.security_changes(before, after)
    assert not gate.security_changes(before, before)


def test_custom_authorization_header_and_operation_id_cannot_silently_change():
    gate = module()
    before = {
        "paths": {
            "/items": {
                "get": {
                    "operationId": "items",
                    "parameters": [
                        {"in": "header", "name": "authorization", "schema": {"type": "string"}}
                    ],
                }
            }
        }
    }
    after = {"paths": {"/items": {"get": {"operationId": "renamed", "parameters": []}}}}
    assert len(gate.security_changes(before, after)) == 2
