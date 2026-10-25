from __future__ import annotations

import difflib
import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from cepio import api
from cepio.management_remote import build_remote_management_router
from cepio.management_runtime import build_management_service


def test_management_snapshot_exact():
    routes = build_remote_management_router(build_management_service(api.runtime)).routes
    actual = get_openapi(title="management", version="v1", routes=routes)
    snapshot = Path(__file__).resolve().parents[1] / "openapi/generated-management-v1.json"
    expected = json.loads(snapshot.read_text(encoding="utf-8"))
    if expected != actual:
        before = json.dumps(expected, indent=2, sort_keys=True).splitlines()
        after = json.dumps(actual, indent=2, sort_keys=True).splitlines()
        diff = list(
            difflib.unified_diff(
                before, after, fromfile="reviewed", tofile="generated", lineterm=""
            )
        )
        raise AssertionError("Management OpenAPI snapshot differs:\n" + "\n".join(diff[:220]))
