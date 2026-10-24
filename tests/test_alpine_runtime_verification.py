"""Negative fixtures prove Alpine support does not bypass runtime security checks."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


minimizer = load("minimize_runtime")
inspector = load("inspect_runtime")


@pytest.fixture
def alpine(tmp_path):
    for name, data in {"lib/apk/db/installed": "honest inventory", "usr/bin/dash": "shell"}.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    (tmp_path / "bin").mkdir()
    try:
        (tmp_path / "bin/sh").symlink_to("../usr/bin/dash")
    except OSError:
        pytest.skip("Symlinks require Linux or Windows developer mode")
    manifest = {
        "inventory": "/lib/apk/db/installed",
        "inventory_sha256": hashlib.sha256(b"honest inventory").hexdigest(),
        "removed_paths": ["/bin/busybox", "/bin/mount"],
        "busybox_sha256": hashlib.sha256(b"busybox fixture").hexdigest(),
        "replaced_shell": {"path": "/bin/sh", "target": "/usr/bin/dash"},
        "vulnerability_waiver": False,
    }
    path = tmp_path / "usr/local/share/cepio/base-evaluation-minimization.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest))
    return tmp_path, path, manifest


def test_alpine_preserves_inventory_and_required_checks(alpine):
    root, _, _ = alpine
    result = minimizer.verify(root)
    assert result["os_inventory_unchanged"] and result["busybox_absent"]
    assert not result["vulnerability_waiver"]


@pytest.mark.parametrize(
    "regression",
    [
        "inventory",
        "waiver",
        "traversal",
        "missing",
        "command",
        "renamed_copy",
        "shell",
        "ambiguous",
    ],
)
def test_alpine_fails_closed(alpine, regression):
    root, path, manifest = alpine
    if regression == "inventory":
        (root / "lib/apk/db/installed").write_text("hidden package")
    elif regression == "waiver":
        manifest["vulnerability_waiver"] = True
    elif regression == "traversal":
        manifest["removed_paths"] = ["/../outside"]
    elif regression == "missing":
        path.unlink()
    elif regression == "command":
        (root / "usr/bin/nsenter").write_text("restored")
    elif regression == "renamed_copy":
        (root / "hidden").write_bytes(b"busybox fixture")
    elif regression == "shell":
        (root / "bin/sh").unlink()
    elif regression == "ambiguous":
        p = root / "var/lib/dpkg/status"
        p.parent.mkdir(parents=True)
        p.write_text("ambiguous")
    if regression != "missing":
        path.write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        minimizer.verify(root)


@pytest.mark.skipif(os.name == "nt", reason="Linux permission and xattr semantics")
@pytest.mark.parametrize("mode", [0o4755, 0o2755])
def test_privileged_files_outside_cli_directories_are_rejected(tmp_path, mode):
    path = tmp_path / "hidden"
    path.write_text("fixture")
    path.chmod(mode)
    with pytest.raises(ValueError, match="PRIVILEGED"):
        inspector.inspect(tmp_path)


def test_capabilities_and_inspection_errors_fail_closed(tmp_path, monkeypatch):
    (tmp_path / "hidden").write_text("fixture")
    monkeypatch.setattr(os, "listxattr", lambda path: ["security.capability"], raising=False)
    with pytest.raises(ValueError, match="CAPABILITIES"):
        inspector.inspect(tmp_path)

    def denied(path):
        raise PermissionError("fixture")

    monkeypatch.setattr(os, "listxattr", denied)
    with pytest.raises(PermissionError):
        inspector.inspect(tmp_path)
