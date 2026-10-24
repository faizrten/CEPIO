from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeSettings:
    environment: str
    db_url: str
    resource_root: str | None
    ontology_dir: str | None
    profiles: tuple[str, ...]
    validate_types: bool
    validate_properties: bool
    strict_properties: bool

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        environment = os.getenv("CEPIO_ENVIRONMENT", "development").strip().lower()
        db_url = os.getenv("CEPIO_DB_URL", "").strip()
        if not db_url:
            if environment in {"development", "test"}:
                db_url = "memory://"
            else:
                raise RuntimeError(
                    "CEPIO_DB_URL is required outside development/test; use sqlite:///path.db "
                    "for the reference persistent runtime or configure a production repository adapter"
                )

        resource_root = os.getenv("CEPIO_RESOURCE_ROOT") or None
        ontology_dir = os.getenv("CEPIO_ONTOLOGY_DIR") or None
        profiles = tuple(
            item.strip() for item in os.getenv("CEPIO_PROFILES", "").split(",") if item.strip()
        )
        return cls(
            environment=environment,
            db_url=db_url,
            resource_root=resource_root,
            ontology_dir=ontology_dir,
            profiles=profiles,
            validate_types=_env_bool("CEPIO_VALIDATE_TYPES", True),
            validate_properties=_env_bool("CEPIO_VALIDATE_PROPERTIES", True),
            strict_properties=_env_bool("CEPIO_STRICT_PROPERTIES", False),
        )

    def sqlite_path(self) -> Path | None:
        if self.db_url == "memory://":
            return None
        prefix = "sqlite:///"
        if self.db_url.startswith(prefix):
            raw = self.db_url[len(prefix) :]
            if not raw:
                raise RuntimeError("CEPIO_DB_URL sqlite path is empty")
            path = Path(raw).expanduser()
            parent = path.resolve().parent
            if not parent.exists():
                raise RuntimeError(f"CEPIO SQLite parent directory does not exist: {parent}")
            return path
        raise RuntimeError(
            "Unsupported CEPIO_DB_URL. The reference runtime supports memory:// and sqlite:///...; "
            "PostgreSQL requires a separately qualified repository adapter"
        )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value")
