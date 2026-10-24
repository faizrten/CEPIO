"""Remove unused CLI entry points after installation; retain libraries and OS inventory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re


TOOLS = (
    "mount",
    "umount",
    "nsenter",
    "unshare",
    "setpriv",
    "runuser",
    "su",
    "login",
    "sulogin",
    "infocmp",
    "tic",
    "toe",
    "tput",
    "tabs",
    "reset",
    "clear",
)
MANIFEST = "usr/local/share/cepio/runtime-minimization.json"


def inventory_hash(root):
    return hashlib.sha256((root / "var/lib/dpkg/status").read_bytes()).hexdigest()


def candidates(root):
    paths = {
        root / directory / name
        for directory in ("bin", "sbin", "usr/bin", "usr/sbin")
        for name in TOOLS
    }
    paths.update((root / "usr/bin").glob("perl*"))
    # Source-package advisories can mention modules absent from perl-base. Check
    # both installed layouts explicitly; do not claim absence without inspection.
    for directory in (root / "usr/share/perl", root / "usr/share/perl5", root / "usr/lib"):
        if directory.exists():
            for path in directory.rglob("*.pm"):
                if path.as_posix().endswith(("/Archive/Tar.pm", "/Pod/Text.pm", "/Text/Wrap.pm")):
                    paths.add(path)
    return sorted(paths)


def minimize(root):
    root = root.resolve()
    before = inventory_hash(root)
    removed = []
    for path in candidates(root):
        # Never traverse a parent symlink outside the selected build/test root.
        if not path.parent.resolve().is_relative_to(root):
            raise ValueError("RUNTIME_PATH_ESCAPES_ROOT")
        if path.is_symlink() or path.is_file():
            path.unlink()
            removed.append(path.relative_to(root).as_posix())
    if before != inventory_hash(root):
        raise ValueError("OS_INVENTORY_CHANGED")
    manifest = {
        "removed_paths": removed,
        "dpkg_status_sha256": before,
        "libraries_and_package_records_retained": True,
        "vulnerability_waiver": False,
    }
    target = root / MANIFEST
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    return verify(root)


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / MANIFEST).read_text())
    remaining = [path for path in candidates(root) if path.exists() or path.is_symlink()]
    if remaining or not manifest.get("removed_paths"):
        raise ValueError("UNMINIMIZED_RUNTIME")
    if manifest.get("dpkg_status_sha256") != inventory_hash(root):
        raise ValueError("OS_INVENTORY_CHANGED")
    # A malformed manifest must never imply qualification or hide arbitrary paths.
    if manifest.get("vulnerability_waiver") is not False or any(
        not re.fullmatch(r"[A-Za-z0-9_./+-]+", p) or ".." in Path(p).parts
        for p in manifest["removed_paths"]
    ):
        raise ValueError("INVALID_MINIMIZATION_MANIFEST")
    return {
        "unused_entrypoints_absent": True,
        "removed_path_count": len(manifest["removed_paths"]),
        "os_inventory_unchanged": True,
        "vulnerability_waiver": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Image build only; default is read-only"
    )
    args = parser.parse_args()
    if args.apply and os.environ.get("CEPIO_IMAGE_BUILD") != "1":
        raise SystemExit("--apply requires CEPIO_IMAGE_BUILD=1 inside the image build")
    print(json.dumps(minimize(Path("/")) if args.apply else verify(Path("/")), sort_keys=True))
