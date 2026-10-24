"""Build-only BusyBox removal; retain installed package records for honest scans."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

from minimize_runtime import candidates

if os.environ.get("CEPIO_IMAGE_BUILD") != "1":
    raise SystemExit("Image build only")

inventory = Path("/lib/apk/db/installed")
before = hashlib.sha256(inventory.read_bytes()).hexdigest()
busybox = Path("/bin/busybox")
dash = Path(shutil.which("dash") or "/missing-dash").resolve()
assert busybox.is_file() and dash.is_file() and dash.name == "dash"
busybox_hash = hashlib.sha256(busybox.read_bytes()).hexdigest()
directories = [Path(p) for p in ("/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin")]
# Resolve all aliases before unlinking their target. Include renamed/hardlinked copies.
paths = [p for directory in directories for p in directory.iterdir()]
aliases = [p for p in paths if p.is_symlink() and p.resolve() == busybox.resolve()]
copies = [
    p
    for p in paths
    if not p.is_symlink()
    and p.is_file()
    and hashlib.sha256(p.read_bytes()).hexdigest() == busybox_hash
]
assert busybox in copies and Path("/bin/sh") in aliases
removed = []
for p in sorted(set(aliases + copies + list(candidates(Path("/"))))):
    if p.is_file() or p.is_symlink():
        p.unlink()
        removed.append(str(p))
Path("/bin/sh").symlink_to(dash)
# Privilege transitions are unnecessary for the service, including optional extras.
for directory, dirs, files in os.walk("/", followlinks=False):
    if directory == "/":
        dirs[:] = [d for d in dirs if d not in {"proc", "sys", "dev"}]
    for name in files:
        p = Path(directory) / name
        metadata = p.lstat()
        if stat.S_ISREG(metadata.st_mode) and metadata.st_mode & 0o6000:
            p.chmod(stat.S_IMODE(metadata.st_mode) & ~0o6000)
assert before == hashlib.sha256(inventory.read_bytes()).hexdigest()
assert not busybox.exists() and Path("/bin/sh").resolve() == dash
manifest = {
    "inventory": str(inventory),
    "inventory_sha256": before,
    "removed_paths": [p for p in removed if p != "/bin/sh"],
    "replaced_shell": {"path": "/bin/sh", "target": str(dash)},
    "busybox_sha256": busybox_hash,
    "busybox_aliases_removed": len(aliases),
    "busybox_copies_removed": len(copies),
    "vulnerability_waiver": False,
}
target = Path("/usr/local/share/cepio/base-evaluation-minimization.json")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(manifest, indent=2) + "\n")
