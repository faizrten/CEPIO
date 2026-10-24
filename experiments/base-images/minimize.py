"""Experiment-only equivalent CLI removal with either dpkg or apk inventory."""
import hashlib
import json
from pathlib import Path

from minimize_runtime import candidates

root = Path("/")
inventory = next(p for p in (Path("/var/lib/dpkg/status"), Path("/lib/apk/db/installed")) if p.is_file())
before = hashlib.sha256(inventory.read_bytes()).hexdigest()
removed = []
for path in candidates(root):
    if path.is_symlink() or path.is_file():
        path.unlink()
        removed.append(str(path))
assert before == hashlib.sha256(inventory.read_bytes()).hexdigest()
assert not any(p.exists() or p.is_symlink() for p in candidates(root))
target = Path("/usr/local/share/cepio/base-evaluation-minimization.json")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps({"inventory": str(inventory), "inventory_sha256": before,
    "removed_paths": removed, "vulnerability_waiver": False}, indent=2) + "\n")
