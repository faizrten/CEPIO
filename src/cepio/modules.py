from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import json
import re

import yaml
from rdflib import Graph, OWL, RDF, RDFS

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class ModuleDependency:
    module: str
    version: str = "*"


@dataclass(frozen=True)
class OntologyModule:
    module_id: str
    namespace: str
    version: str
    file: str
    tier: str
    stability: str = "experimental"
    dependencies: tuple[ModuleDependency, ...] = ()


@dataclass
class ModuleCatalogue:
    schema_version: str
    modules: dict[str, OntologyModule] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "ModuleCatalogue":
        path = Path(path)
        raw = yaml.safe_load(path.read_text()) or {}
        modules: dict[str, OntologyModule] = {}
        for item in raw.get("modules", []):
            module_id = item.get("id") or item.get("name")
            if not module_id:
                raise ValueError("Every ontology module requires id/name")
            deps = tuple(ModuleDependency(module=(d if isinstance(d, str) else d["module"]), version=("*" if isinstance(d, str) else d.get("version", "*"))) for d in item.get("depends_on", []))
            mod = OntologyModule(module_id=module_id, namespace=item["namespace"], version=str(item["version"]), file=item["file"], tier=item["tier"], stability=item.get("stability", "experimental"), dependencies=deps)
            if module_id in modules:
                raise ValueError(f"Duplicate ontology module id: {module_id}")
            modules[module_id] = mod
        catalogue = cls(schema_version=str(raw.get("schema_version", "1")), modules=modules)
        catalogue.validate(path.parent)
        return catalogue

    def validate(self, root: str | Path) -> None:
        root = Path(root)
        seen_namespaces: dict[str, str] = {}
        for module_id, mod in self.modules.items():
            if not SEMVER_RE.match(mod.version):
                raise ValueError(f"Module {module_id} has invalid semantic version: {mod.version}")
            if mod.namespace in seen_namespaces:
                raise ValueError(f"Namespace {mod.namespace} reused by {seen_namespaces[mod.namespace]} and {module_id}")
            seen_namespaces[mod.namespace] = module_id
            if not (root / mod.file).exists():
                raise ValueError(f"Module {module_id} file does not exist: {mod.file}")
            for dep in mod.dependencies:
                if dep.module not in self.modules:
                    raise ValueError(f"Module {module_id} depends on unknown module {dep.module}")
                if not _satisfies(self.modules[dep.module].version, dep.version):
                    raise ValueError(f"Module {module_id} requires {dep.module} {dep.version}, found {self.modules[dep.module].version}")
        self.topological_order()

    def topological_order(self) -> list[str]:
        visiting: set[str] = set()
        visited: set[str] = set()
        ordered: list[str] = []
        def visit(module_id: str) -> None:
            if module_id in visited: return
            if module_id in visiting: raise ValueError(f"Ontology module dependency cycle detected at {module_id}")
            visiting.add(module_id)
            for dep in self.modules[module_id].dependencies: visit(dep.module)
            visiting.remove(module_id); visited.add(module_id); ordered.append(module_id)
        for module_id in sorted(self.modules): visit(module_id)
        return ordered

    def graph(self, root: str | Path) -> Graph:
        root = Path(root); graph = Graph()
        for module_id in self.topological_order(): graph.parse(root / self.modules[module_id].file, format="turtle")
        return graph

    def snapshot(self, root: str | Path) -> dict:
        root = Path(root); modules: dict[str, dict] = {}
        for module_id in self.topological_order():
            mod = self.modules[module_id]; graph = Graph(); graph.parse(root / mod.file, format="turtle")
            modules[module_id] = {
                "version": mod.version, "namespace": mod.namespace,
                "classes": sorted(str(s) for s in graph.subjects(RDF.type, OWL.Class)),
                "relationships": sorted(str(s) for s in graph.subjects(RDF.type, OWL.ObjectProperty)),
                "parents": sorted((str(s), str(o)) for s, o in graph.subject_objects(RDFS.subClassOf)),
                "domains": sorted((str(s), str(o)) for s, o in graph.subject_objects(RDFS.domain)),
                "ranges": sorted((str(s), str(o)) for s, o in graph.subject_objects(RDFS.range)),
                "sha256": sha256((root / mod.file).read_bytes()).hexdigest(),
            }
        return {"schema_version": self.schema_version, "modules": modules}

    def write_snapshot(self, root: str | Path, output: str | Path) -> None:
        Path(output).write_text(json.dumps(self.snapshot(root), indent=2, sort_keys=True) + "\n")


def _version_tuple(version: str) -> tuple[int, int, int]:
    core = version.split("-", 1)[0].split("+", 1)[0]
    return tuple(int(x) for x in core.split("."))


def _satisfies(version: str, constraint: str) -> bool:
    if constraint in ("", "*"): return True
    v = _version_tuple(version)
    for clause in [c.strip() for c in constraint.split(",") if c.strip()]:
        if clause.startswith(">="): ok = v >= _version_tuple(clause[2:])
        elif clause.startswith("<="): ok = v <= _version_tuple(clause[2:])
        elif clause.startswith(">"): ok = v > _version_tuple(clause[1:])
        elif clause.startswith("<"): ok = v < _version_tuple(clause[1:])
        elif clause.startswith("=="): ok = v == _version_tuple(clause[2:])
        else: ok = v == _version_tuple(clause)
        if not ok: return False
    return True


def compare_snapshots(old: dict, new: dict) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"additive": [], "breaking": []}
    old_modules, new_modules = old.get("modules", {}), new.get("modules", {})
    for module_id in sorted(set(old_modules) | set(new_modules)):
        if module_id not in new_modules:
            result["breaking"].append(f"module removed: {module_id}"); continue
        if module_id not in old_modules:
            result["additive"].append(f"module added: {module_id}"); continue
        before, after = old_modules[module_id], new_modules[module_id]
        for field_name, label in [("classes", "class"), ("relationships", "relationship")]:
            b, a = set(before.get(field_name, [])), set(after.get(field_name, []))
            result["breaking"].extend(f"{label} removed: {x}" for x in sorted(b - a))
            result["additive"].extend(f"{label} added: {x}" for x in sorted(a - b))
        for field_name, label in [("parents", "subclass edge"), ("domains", "domain constraint"), ("ranges", "range constraint")]:
            b = {tuple(x) for x in before.get(field_name, [])}; a = {tuple(x) for x in after.get(field_name, [])}
            result["breaking"].extend(f"{label} removed: {x}" for x in sorted(b - a))
            result["additive"].extend(f"{label} added: {x}" for x in sorted(a - b))
    return result
