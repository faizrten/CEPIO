from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rdflib import Graph

from .modules import ModuleCatalogue, _satisfies


@dataclass(frozen=True)
class ProfileFiles:
    ontology: tuple[str, ...] = ()
    mappings: tuple[str, ...] = ()
    property_mappings: tuple[str, ...] = ()
    kpis: tuple[str, ...] = ()
    shapes: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    bindings: dict[str, str] = field(default_factory=dict)
    sample_data: tuple[str, ...] = ()

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> "ProfileFiles":
        raw = raw or {}
        return cls(
            ontology=_as_tuple(raw.get("ontology")),
            mappings=_as_tuple(raw.get("mappings")),
            property_mappings=_as_tuple(raw.get("property_mappings")),
            kpis=_as_tuple(raw.get("kpis")),
            shapes=_as_tuple(raw.get("shapes")),
            actions=_as_tuple(raw.get("actions")),
            policies=_as_tuple(raw.get("policies")),
            bindings={str(k): str(v) for k, v in (raw.get("bindings") or {}).items()},
            sample_data=_as_tuple(raw.get("sample_data")),
        )

    def all_relative_paths(self) -> tuple[str, ...]:
        values: list[str] = []
        for group in (
            self.ontology,
            self.mappings,
            self.property_mappings,
            self.kpis,
            self.shapes,
            self.actions,
            self.policies,
            self.sample_data,
        ):
            values.extend(group)
        values.extend(self.bindings.values())
        return tuple(values)


@dataclass(frozen=True)
class ProfileManifest:
    profile_id: str
    version: str
    schema_version: str
    namespace: str | None
    description: str | None
    depends_on: dict[str, str]
    files: ProfileFiles
    root: Path

    @classmethod
    def load(cls, path: str | Path) -> "ProfileManifest":
        path = Path(path)
        raw = yaml.safe_load(path.read_text()) or {}
        profile_id = raw.get("id")
        version = raw.get("version")
        if not profile_id or not version:
            raise ValueError(f"Profile manifest {path} requires id and version")
        namespace = str(raw["namespace"]) if raw.get("namespace") else None
        if namespace and not (namespace.startswith("http://") or namespace.startswith("https://")):
            raise ValueError(f"Profile {profile_id} namespace must be an absolute HTTP(S) IRI")
        manifest = cls(
            profile_id=str(profile_id),
            version=str(version),
            schema_version=str(raw.get("schema_version", "1")),
            namespace=namespace,
            description=str(raw["description"]) if raw.get("description") else None,
            depends_on={str(k): str(v) for k, v in (raw.get("depends_on") or {}).items()},
            files=ProfileFiles.from_raw(raw.get("files")),
            root=path.parent,
        )
        manifest.validate_files()
        return manifest

    def validate_files(self) -> None:
        missing = [relative for relative in self.files.all_relative_paths() if not (self.root / relative).exists()]
        if missing:
            raise ValueError(
                f"Profile {self.profile_id} references missing files: {sorted(missing)}"
            )

    def validate_dependencies(self, catalogue: ModuleCatalogue) -> None:
        for module_id, constraint in self.depends_on.items():
            module = catalogue.modules.get(module_id)
            if module is None:
                raise ValueError(
                    f"Profile {self.profile_id} depends on unknown canonical module {module_id}"
                )
            if not _satisfies(module.version, constraint):
                raise ValueError(
                    f"Profile {self.profile_id} requires {module_id} {constraint}; found {module.version}"
                )

    def add_ontology_to_graph(self, graph: Graph) -> None:
        for relative in self.files.ontology:
            graph.parse(self.root / relative, format="turtle")

    def binding_path(self, target: str) -> Path | None:
        relative = self.files.bindings.get(target)
        return self.root / relative if relative else None

    def owns_iri(self, iri: str) -> bool:
        return bool(self.namespace and iri.startswith(self.namespace))


class ProfileRegistry:
    def __init__(self, profiles_root: str | Path, catalogue: ModuleCatalogue) -> None:
        self.profiles_root = Path(profiles_root)
        self.catalogue = catalogue

    def load(self, profile_ids: tuple[str, ...] | list[str]) -> list[ProfileManifest]:
        loaded: list[ProfileManifest] = []
        seen: set[str] = set()
        for requested in profile_ids:
            profile_id = str(requested).strip()
            if not profile_id:
                continue
            if profile_id in seen:
                continue
            manifest_path = self.profiles_root / profile_id / "profile.yaml"
            if not manifest_path.exists():
                raise ValueError(f"Unknown CEPIO customer profile: {profile_id}")
            manifest = ProfileManifest.load(manifest_path)
            if manifest.profile_id != profile_id:
                raise ValueError(
                    f"Profile directory '{profile_id}' contains manifest id '{manifest.profile_id}'"
                )
            manifest.validate_dependencies(self.catalogue)
            loaded.append(manifest)
            seen.add(profile_id)
        return loaded


def build_profiled_graph(
    canonical_root: str | Path,
    catalogue: ModuleCatalogue,
    profiles: list[ProfileManifest],
) -> Graph:
    graph = catalogue.graph(canonical_root)
    for profile in profiles:
        profile.add_ontology_to_graph(graph)
    return graph


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise ValueError(f"Profile file declaration must be a string or list, got {type(value).__name__}")
