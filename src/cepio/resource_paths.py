from __future__ import annotations

import os
from importlib import resources
from pathlib import Path


def resolve_resource_root(explicit: str | Path | None = None) -> Path:
    """Resolve CEPIO runtime assets.

    Resolution order:
    1. explicit argument;
    2. CEPIO_RESOURCE_ROOT;
    3. packaged `cepio.resources` bundle populated in wheel builds;
    4. repository root fallback for editable/source development.
    """

    candidate = explicit or os.getenv("CEPIO_RESOURCE_ROOT")
    if candidate:
        root = Path(candidate).expanduser().resolve()
        _validate_root(root)
        return root

    packaged = resources.files("cepio.resources")
    if (packaged / "ontology-modules.yaml").is_file():
        root = Path(str(packaged))
        _validate_root(root)
        return root

    repo_root = Path(__file__).resolve().parents[2]
    _validate_root(repo_root)
    return repo_root


def _validate_root(root: Path) -> None:
    required = [
        root / "ontology-modules.yaml",
        root / "ontologies",
        root / "policies" / "policies.yaml",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "CEPIO resource root is incomplete; missing: " + ", ".join(missing)
        )
