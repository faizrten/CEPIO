"""Read-only, fail-closed privilege inspection without distribution CLI tools."""

import json
import os
from pathlib import Path
import stat


def fail(error):
    raise error


def regular_files(root):
    """Walk the image filesystem without following links or mounted filesystems."""
    device = root.stat().st_dev
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        dirs[:] = [name for name in dirs if (Path(directory) / name).lstat().st_dev == device]
        for name in files:
            path = Path(directory) / name
            metadata = path.lstat()
            if metadata.st_dev == device and stat.S_ISREG(metadata.st_mode):
                yield path, metadata


def inspect(root):
    for path, metadata in regular_files(root):
        if metadata.st_mode & 0o6000:
            raise ValueError("PRIVILEGED_RUNTIME_FILES_PRESENT")
        if "security.capability" in os.listxattr(path):
            raise ValueError("RUNTIME_FILE_CAPABILITIES_PRESENT")
    return {"setuid_setgid_files": 0, "file_capabilities": 0}


if __name__ == "__main__":
    print(json.dumps(inspect(Path("/")), sort_keys=True))
