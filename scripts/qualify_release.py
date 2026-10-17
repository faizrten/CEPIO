"""Produce a Developer Preview qualification manifest, never a production claim."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from cepio._version import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    if args.tag and args.tag != f"v{__version__}":
        raise ValueError(f"Tag {args.tag} does not match package version v{__version__}")
    for required in ["RELEASE.md", "docs/migrations-and-compatibility.md"]:
        if not Path(required).read_text(encoding="utf-8").strip():
            raise ValueError(f"Missing release/migration notes: {required}")
    wheels = list(Path("dist").glob(f"cepio-{__version__}-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one wheel matching the package version")
    required_evidence = [
        "evidence/container-sbom.json",
        "evidence/container-vulnerabilities.json",
        "evidence/python-sbom.json",
    ]
    for path in required_evidence:
        json.loads(Path(path).read_text(encoding="utf-8"))
    artifacts = (
        wheels + list(Path("dist").glob("*.tar")) + [Path(path) for path in required_evidence]
    )
    if not any(path.suffix == ".tar" for path in artifacts):
        raise ValueError("Missing qualified container archive")
    manifest = {
        "schema_version": 1,
        "version": __version__,
        "qualification": "developer-preview",
        "production_qualified": False,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "tag": args.tag or None,
        "artifacts": {path.as_posix(): digest(path) for path in artifacts},
    }
    Path("evidence/release-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
