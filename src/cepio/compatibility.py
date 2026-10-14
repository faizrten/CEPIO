from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import subprocess
import tarfile
import tempfile
from typing import Any

import yaml

from .modules import ModuleCatalogue, _version_tuple


@dataclass(frozen=True)
class ContractChange:
    key: str
    kind: str
    module: str
    subject: str
    message: str
    breaking: bool
    before: Any | None = None
    after: Any | None = None


@dataclass(frozen=True)
class MigrationDeclaration:
    change: str
    rationale: str
    strategy: str
    replacement: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class MigrationManifest:
    schema_version: str
    migration_id: str
    from_ref: str
    description: str
    issue: str | None
    declarations: tuple[MigrationDeclaration, ...]
    path: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> "MigrationManifest":
        path = Path(path)
        raw = yaml.safe_load(path.read_text()) or {}
        migration_id = raw.get("id")
        from_ref = raw.get("from_ref")
        if not migration_id or not from_ref:
            raise ValueError(f"Migration manifest {path} requires id and from_ref")
        if not raw.get("description"):
            raise ValueError(f"Migration manifest {path} requires description")
        declarations: list[MigrationDeclaration] = []
        allowed_strategies = {
            "alias",
            "rewrite",
            "dual-read",
            "manual",
            "deprecate-then-remove",
            "no-data-impact",
        }
        for item in raw.get("changes", []):
            for required in ("change", "rationale", "strategy"):
                if not item.get(required):
                    raise ValueError(
                        f"Migration manifest {path} change requires {required}"
                    )
            if str(item["strategy"]) not in allowed_strategies:
                raise ValueError(
                    f"Migration manifest {path} uses unsupported strategy {item['strategy']}"
                )
            declarations.append(
                MigrationDeclaration(
                    change=str(item["change"]),
                    rationale=str(item["rationale"]),
                    strategy=str(item["strategy"]),
                    replacement=item.get("replacement"),
                    notes=item.get("notes"),
                )
            )
        if not declarations:
            raise ValueError(f"Migration manifest {path} declares no changes")
        return cls(
            schema_version=str(raw.get("schema_version", "1")),
            migration_id=str(migration_id),
            from_ref=str(from_ref),
            description=str(raw.get("description", "")),
            issue=(str(raw["issue"]) if raw.get("issue") else None),
            declarations=tuple(declarations),
            path=str(path),
        )


@dataclass(frozen=True)
class BaselineConfig:
    schema_version: str
    accepted_ref: str
    label: str
    manifest: str = "ontology-modules.yaml"
    migrations_dir: str = "compatibility/migrations"

    @classmethod
    def load(cls, path: str | Path) -> "BaselineConfig":
        path = Path(path)
        raw = yaml.safe_load(path.read_text()) or {}
        accepted = raw.get("accepted_contract") or {}
        ref = accepted.get("ref")
        if not ref:
            raise ValueError(f"Baseline config {path} requires accepted_contract.ref")
        return cls(
            schema_version=str(raw.get("schema_version", "1")),
            accepted_ref=str(ref),
            label=str(accepted.get("label", ref)),
            manifest=str(accepted.get("manifest", "ontology-modules.yaml")),
            migrations_dir=str(raw.get("migrations_dir", "compatibility/migrations")),
        )


@dataclass
class CompatibilityReport:
    baseline_ref: str
    baseline_label: str
    changes: list[ContractChange] = field(default_factory=list)
    declared_breaking: list[ContractChange] = field(default_factory=list)
    undeclared_breaking: list[ContractChange] = field(default_factory=list)
    additive: list[ContractChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stale_declarations: list[str] = field(default_factory=list)

    @property
    def compatible(self) -> bool:
        return not self.undeclared_breaking and not self.errors and not self.stale_declarations

    def to_dict(self) -> dict[str, Any]:
        def encode(change: ContractChange) -> dict[str, Any]:
            return {
                "key": change.key,
                "kind": change.kind,
                "module": change.module,
                "subject": change.subject,
                "message": change.message,
                "breaking": change.breaking,
                "before": change.before,
                "after": change.after,
            }

        return {
            "baseline_ref": self.baseline_ref,
            "baseline_label": self.baseline_label,
            "compatible": self.compatible,
            "additive": [encode(c) for c in self.additive],
            "declared_breaking": [encode(c) for c in self.declared_breaking],
            "undeclared_breaking": [encode(c) for c in self.undeclared_breaking],
            "errors": self.errors,
            "stale_declarations": self.stale_declarations,
        }


def _edge_key(kind: str, module: str, edge: tuple[str, str]) -> str:
    return f"{kind}:{module}:{edge[0]}->{edge[1]}"


def analyze_snapshots(old: dict, new: dict) -> list[ContractChange]:
    changes: list[ContractChange] = []
    old_modules = old.get("modules", {})
    new_modules = new.get("modules", {})

    def add(
        *,
        kind: str,
        module: str,
        subject: str,
        message: str,
        breaking: bool,
        before: Any | None = None,
        after: Any | None = None,
        key: str | None = None,
    ) -> None:
        changes.append(
            ContractChange(
                key=key or f"{kind}:{module}:{subject}",
                kind=kind,
                module=module,
                subject=subject,
                message=message,
                breaking=breaking,
                before=before,
                after=after,
            )
        )

    for module_id in sorted(set(old_modules) | set(new_modules)):
        if module_id not in new_modules:
            add(
                kind="module_removed",
                module=module_id,
                subject=module_id,
                message=f"module removed: {module_id}",
                breaking=True,
            )
            continue
        if module_id not in old_modules:
            add(
                kind="module_added",
                module=module_id,
                subject=module_id,
                message=f"module added: {module_id}",
                breaking=False,
            )
            continue

        before = old_modules[module_id]
        after = new_modules[module_id]
        old_ns = before.get("namespace")
        new_ns = after.get("namespace")
        if old_ns != new_ns:
            add(
                kind="namespace_changed",
                module=module_id,
                subject=module_id,
                message=f"namespace changed for {module_id}: {old_ns} -> {new_ns}",
                breaking=True,
                before=old_ns,
                after=new_ns,
            )

        for field_name, label, removed_kind, added_kind in [
            ("classes", "class", "class_removed", "class_added"),
            ("relationships", "relationship", "relationship_removed", "relationship_added"),
            (
                "datatype_properties",
                "datatype property",
                "datatype_property_removed",
                "datatype_property_added",
            ),
        ]:
            b = set(before.get(field_name, []))
            a = set(after.get(field_name, []))
            for item in sorted(b - a):
                add(
                    kind=removed_kind,
                    module=module_id,
                    subject=item,
                    message=f"{label} removed: {item}",
                    breaking=True,
                )
            for item in sorted(a - b):
                add(
                    kind=added_kind,
                    module=module_id,
                    subject=item,
                    message=f"{label} added: {item}",
                    breaking=False,
                )

        existing_subjects = (
            set(before.get("relationships", []))
            | set(before.get("datatype_properties", []))
            | set(before.get("classes", []))
        )
        for field_name, label, removed_kind, added_kind in [
            ("parents", "subclass edge", "subclass_edge_removed", "subclass_edge_added"),
            ("domains", "domain constraint", "domain_constraint_removed", "domain_constraint_added"),
            ("ranges", "range constraint", "range_constraint_removed", "range_constraint_added"),
            (
                "datatype_ranges",
                "datatype range",
                "datatype_range_removed",
                "datatype_range_added",
            ),
        ]:
            b = {tuple(x) for x in before.get(field_name, [])}
            a = {tuple(x) for x in after.get(field_name, [])}
            for edge in sorted(b - a):
                add(
                    kind=removed_kind,
                    module=module_id,
                    subject=edge[0],
                    message=f"{label} removed: {edge}",
                    breaking=True,
                    before=edge,
                    key=_edge_key(removed_kind, module_id, edge),
                )
            for edge in sorted(a - b):
                is_breaking = edge[0] in existing_subjects
                add(
                    kind=added_kind,
                    module=module_id,
                    subject=edge[0],
                    message=f"{label} added: {edge}",
                    breaking=is_breaking,
                    after=edge,
                    key=_edge_key(added_kind, module_id, edge),
                )

    if old.get("property_contract") != new.get("property_contract"):
        add(
            kind="property_contract_path_changed",
            module="_contract",
            subject="property_contract",
            message=(
                f"property contract path changed: {old.get('property_contract')} "
                f"-> {new.get('property_contract')}"
            ),
            breaking=True,
            before=old.get("property_contract"),
            after=new.get("property_contract"),
        )
    return changes


def _required_bump(old_version: str, *, breaking: bool) -> str:
    major, _, _ = _version_tuple(old_version)
    if breaking:
        return "minor-or-major" if major == 0 else "major"
    return "patch-or-higher"


def _version_satisfies_change(old_version: str, new_version: str, *, breaking: bool) -> bool:
    old_v = _version_tuple(old_version)
    new_v = _version_tuple(new_version)
    if new_v <= old_v:
        return False
    if not breaking:
        return True
    if old_v[0] == 0:
        return new_v[0] > old_v[0] or new_v[1] > old_v[1]
    return new_v[0] > old_v[0]


def validate_module_versions(old: dict, new: dict, changes: list[ContractChange]) -> list[str]:
    errors: list[str] = []
    old_modules = old.get("modules", {})
    new_modules = new.get("modules", {})
    by_module: dict[str, list[ContractChange]] = {}
    for change in changes:
        if change.module in old_modules and change.module in new_modules:
            by_module.setdefault(change.module, []).append(change)

    for module_id, module_changes in sorted(by_module.items()):
        semantic_changes = [
            c
            for c in module_changes
            if c.kind not in {"module_added"} and c.kind != "module_removed"
        ]
        if not semantic_changes:
            continue
        old_version = str(old_modules[module_id].get("version", "0.0.0"))
        new_version = str(new_modules[module_id].get("version", "0.0.0"))
        breaking = any(c.breaking for c in semantic_changes)
        if not _version_satisfies_change(old_version, new_version, breaking=breaking):
            errors.append(
                f"module {module_id} changed semantically but version {old_version} -> "
                f"{new_version} does not satisfy required {_required_bump(old_version, breaking=breaking)} bump"
            )
    return errors


def load_migrations(directory: str | Path, *, baseline_ref: str) -> list[MigrationManifest]:
    directory = Path(directory)
    if not directory.exists():
        return []
    manifests: list[MigrationManifest] = []
    seen_ids: set[str] = set()
    for path in sorted(directory.glob("*.yaml")):
        manifest = MigrationManifest.load(path)
        if manifest.from_ref != baseline_ref:
            continue
        if manifest.migration_id in seen_ids:
            raise ValueError(f"Duplicate migration id: {manifest.migration_id}")
        seen_ids.add(manifest.migration_id)
        manifests.append(manifest)
    return manifests


def evaluate_compatibility(
    old: dict,
    new: dict,
    *,
    baseline_ref: str,
    baseline_label: str,
    migrations: list[MigrationManifest] | None = None,
) -> CompatibilityReport:
    changes = analyze_snapshots(old, new)
    report = CompatibilityReport(
        baseline_ref=baseline_ref,
        baseline_label=baseline_label,
        changes=changes,
    )
    report.errors.extend(validate_module_versions(old, new, changes))

    declarations: dict[str, MigrationDeclaration] = {}
    for manifest in migrations or []:
        for declaration in manifest.declarations:
            if declaration.change in declarations:
                report.errors.append(
                    f"breaking change declared more than once: {declaration.change}"
                )
            declarations[declaration.change] = declaration

    detected_breaking = {change.key: change for change in changes if change.breaking}
    report.additive.extend(change for change in changes if not change.breaking)
    for key, change in detected_breaking.items():
        if key in declarations:
            report.declared_breaking.append(change)
        else:
            report.undeclared_breaking.append(change)

    report.stale_declarations.extend(
        key for key in sorted(declarations) if key not in detected_breaking
    )
    return report


def snapshot_from_git_ref(
    repo_root: str | Path,
    git_ref: str,
    *,
    manifest_path: str = "ontology-modules.yaml",
) -> dict:
    repo_root = Path(repo_root).resolve()
    with tempfile.TemporaryDirectory(prefix="cepio-contract-") as tmp:
        archive = subprocess.run(
            ["git", "-C", str(repo_root), "archive", "--format=tar", git_ref],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tmp_root = Path(tmp)
        tar_path = tmp_root / "repo.tar"
        tar_path.write_bytes(archive.stdout)
        exported_root = tmp_root / "repo"
        exported_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path) as tf:
            for member in tf.getmembers():
                member_path = Path(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValueError(f"Unsafe path in git archive: {member.name}")
            tf.extractall(exported_root)
        catalogue = ModuleCatalogue.load(exported_root / manifest_path)
        return catalogue.snapshot(exported_root)


def check_repository_contract(
    repo_root: str | Path,
    *,
    baseline_config_path: str | Path = "compatibility/baseline.yaml",
    manifest_path: str = "ontology-modules.yaml",
    migrations_dir: str | Path | None = None,
) -> CompatibilityReport:
    repo_root = Path(repo_root).resolve()
    config = BaselineConfig.load(repo_root / baseline_config_path)
    old = snapshot_from_git_ref(
        repo_root,
        config.accepted_ref,
        manifest_path=config.manifest,
    )
    catalogue = ModuleCatalogue.load(repo_root / manifest_path)
    new = catalogue.snapshot(repo_root)
    migration_path = repo_root / (migrations_dir or config.migrations_dir)
    migrations = load_migrations(migration_path, baseline_ref=config.accepted_ref)
    return evaluate_compatibility(
        old,
        new,
        baseline_ref=config.accepted_ref,
        baseline_label=config.label,
        migrations=migrations,
    )


def write_report(report: CompatibilityReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n")
