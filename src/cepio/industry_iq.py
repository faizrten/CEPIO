from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Protocol

from pydantic import BaseModel, Field

from ._version import __version__
from .runtime import CEPIORuntime


_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class IndustryIQPackManifest(BaseModel):
    """Machine-readable contract for one versioned Industry IQ pack."""

    pack_id: str
    version: str
    requires_core: str = "*"
    requires_packs: dict[str, str] = Field(default_factory=dict)
    functions: set[str] = Field(default_factory=set)
    decisions: set[str] = Field(default_factory=set)
    actions: set[str] = Field(default_factory=set)


class IndustryIQResolution(BaseModel):
    """Deterministic dependency-resolution result before runtime mutation."""

    core_version: str
    requested: dict[str, str]
    selected: dict[str, str]
    install_order: list[str]


class IndustryIQDeploymentManifest(BaseModel):
    """Resolved pack deployment captured after successful installation."""

    core_version: str
    packs: dict[str, IndustryIQPackManifest]
    install_order: list[str]


class IndustryIQResolutionError(ValueError):
    """Fail-closed pack discovery, compatibility, or composition failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IndustryIQPack(Protocol):
    """Runtime extension contract for domain/industry intelligence.

    CEPIO Core owns the governed runtime mechanics. Industry IQ packs register
    domain-specific functions, decisions and actions without making them permanent
    Core capabilities. Existing v0.4 packs remain valid; a richer ``manifest`` is
    optional and synthesized from ``pack_id``/``version`` when absent.
    """

    pack_id: str
    version: str

    def install(self, runtime: CEPIORuntime) -> None: ...


def _parse_semver(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"Industry IQ versions must use stable MAJOR.MINOR.PATCH SemVer: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def version_satisfies(version: str, constraint: str) -> bool:
    """Evaluate the small deterministic SemVer constraint language used by packs.

    Supported forms: ``*``, exact versions, comma-separated ``>=``, ``<=``, ``>``,
    ``<`` and ``==`` clauses, plus caret (``^``) and tilde (``~``) ranges.
    """

    current = _parse_semver(version)
    expression = constraint.strip()
    if expression in {"", "*"}:
        return True

    for raw_clause in expression.split(","):
        clause = raw_clause.strip()
        if not clause:
            continue
        if clause.startswith("^"):
            lower = _parse_semver(clause[1:])
            major, minor, patch = lower
            if major > 0:
                upper = (major + 1, 0, 0)
            elif minor > 0:
                upper = (0, minor + 1, 0)
            else:
                upper = (0, 0, patch + 1)
            if not (lower <= current < upper):
                return False
            continue
        if clause.startswith("~"):
            lower = _parse_semver(clause[1:])
            upper = (lower[0], lower[1] + 1, 0)
            if not (lower <= current < upper):
                return False
            continue

        operator = "=="
        target_text = clause
        for candidate in (">=", "<=", "==", ">", "<", "="):
            if clause.startswith(candidate):
                operator = "==" if candidate == "=" else candidate
                target_text = clause[len(candidate) :].strip()
                break
        target = _parse_semver(target_text)
        comparisons = {
            ">=": current >= target,
            "<=": current <= target,
            ">": current > target,
            "<": current < target,
            "==": current == target,
        }
        if not comparisons[operator]:
            return False
    return True


def industry_iq_manifest(pack: IndustryIQPack) -> IndustryIQPackManifest:
    """Return a validated manifest while preserving compatibility with v0.4 packs."""

    raw = getattr(pack, "manifest", None)
    if raw is None:
        manifest = IndustryIQPackManifest(pack_id=pack.pack_id, version=pack.version)
    elif isinstance(raw, IndustryIQPackManifest):
        manifest = raw
    else:
        manifest = IndustryIQPackManifest.model_validate(raw)

    if manifest.pack_id != pack.pack_id or manifest.version != pack.version:
        raise ValueError(
            "Industry IQ pack manifest identity must match pack_id/version attributes"
        )
    _parse_semver(manifest.version)
    return manifest


class IndustryIQPackRegistry:
    """Discover, resolve, compose and install versioned Industry IQ packs.

    Resolution is side-effect free. All dependency, core-compatibility and capability
    collision checks are completed before any selected pack is allowed to mutate the
    CEPIO runtime.
    """

    def __init__(self, *, core_version: str = __version__) -> None:
        _parse_semver(core_version)
        self.core_version = core_version
        self._packs: dict[str, dict[str, IndustryIQPack]] = {}

    def register(self, pack: IndustryIQPack) -> None:
        manifest = industry_iq_manifest(pack)
        versions = self._packs.setdefault(manifest.pack_id, {})
        if manifest.version in versions:
            raise IndustryIQResolutionError(
                "PACK_VERSION_ALREADY_REGISTERED",
                f"Industry IQ pack already registered: {manifest.pack_id}@{manifest.version}",
            )
        versions[manifest.version] = pack

    def manifests(self) -> list[IndustryIQPackManifest]:
        result: list[IndustryIQPackManifest] = []
        for pack_id in sorted(self._packs):
            versions = self._packs[pack_id]
            for version in sorted(versions, key=_parse_semver, reverse=True):
                result.append(industry_iq_manifest(versions[version]))
        return result

    def resolve(
        self, requested: Iterable[str] | Mapping[str, str]
    ) -> IndustryIQResolution:
        request_map = self._normalize_requested(requested)
        constraints: dict[str, list[str]] = {
            pack_id: [constraint] for pack_id, constraint in request_map.items()
        }
        selected = self._solve({}, constraints)
        if selected is None:
            rendered = ", ".join(
                f"{pack_id}{constraint if constraint != '*' else ''}"
                for pack_id, constraint in sorted(request_map.items())
            )
            raise IndustryIQResolutionError(
                "PACK_RESOLUTION_FAILED",
                f"No compatible Industry IQ pack composition satisfies: {rendered}",
            )

        install_order = self._install_order(selected)
        return IndustryIQResolution(
            core_version=self.core_version,
            requested=dict(sorted(request_map.items())),
            selected={
                pack_id: industry_iq_manifest(pack).version
                for pack_id, pack in sorted(selected.items())
            },
            install_order=install_order,
        )

    def install(
        self,
        runtime: CEPIORuntime,
        requested: Iterable[str] | Mapping[str, str],
    ) -> IndustryIQDeploymentManifest:
        resolution = self.resolve(requested)
        selected = {
            pack_id: self._packs[pack_id][version]
            for pack_id, version in resolution.selected.items()
        }

        already_installed = set(runtime.industry_iq_packs).intersection(selected)
        if already_installed:
            pack_id = sorted(already_installed)[0]
            raise IndustryIQResolutionError(
                "PACK_ALREADY_INSTALLED",
                f"Industry IQ pack already installed in runtime: {pack_id}",
            )

        manifests = {
            pack_id: industry_iq_manifest(pack) for pack_id, pack in selected.items()
        }
        self._validate_capability_collisions(runtime, manifests)

        for pack_id in resolution.install_order:
            pack = selected[pack_id]
            pack.install(runtime)
            runtime.industry_iq_packs[pack_id] = manifests[pack_id].version

        runtime.industry_iq_packs = dict(sorted(runtime.industry_iq_packs.items()))
        deployment = IndustryIQDeploymentManifest(
            core_version=self.core_version,
            packs={pack_id: manifests[pack_id] for pack_id in sorted(manifests)},
            install_order=resolution.install_order,
        )
        setattr(runtime, "industry_iq_deployment_manifest", deployment)
        return deployment

    def _normalize_requested(
        self, requested: Iterable[str] | Mapping[str, str]
    ) -> dict[str, str]:
        if isinstance(requested, Mapping):
            normalized = {str(pack_id): str(constraint) for pack_id, constraint in requested.items()}
        else:
            normalized = {str(pack_id): "*" for pack_id in requested}
        if not normalized:
            return {}
        for pack_id, constraint in normalized.items():
            if not pack_id:
                raise ValueError("Industry IQ pack ID cannot be empty")
            if constraint not in {"", "*"}:
                # Exercise the parser now so malformed requirements fail before resolution.
                sample = next(iter(self._packs.get(pack_id, {"0.0.0": None})))
                try:
                    version_satisfies(sample, constraint)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid Industry IQ version constraint for {pack_id}: {constraint}"
                    ) from exc
        return normalized

    def _solve(
        self,
        selected: dict[str, IndustryIQPack],
        constraints: dict[str, list[str]],
    ) -> dict[str, IndustryIQPack] | None:
        for pack_id, pack in selected.items():
            version = industry_iq_manifest(pack).version
            if not all(version_satisfies(version, item) for item in constraints.get(pack_id, [])):
                return None

        unresolved = sorted(pack_id for pack_id in constraints if pack_id not in selected)
        if not unresolved:
            return selected

        pack_id = unresolved[0]
        versions = self._packs.get(pack_id)
        if not versions:
            return None

        required = constraints[pack_id]
        candidates = sorted(versions, key=_parse_semver, reverse=True)
        for version in candidates:
            if not all(version_satisfies(version, item) for item in required):
                continue
            pack = versions[version]
            manifest = industry_iq_manifest(pack)
            if not version_satisfies(self.core_version, manifest.requires_core):
                continue

            next_selected = dict(selected)
            next_selected[pack_id] = pack
            next_constraints = {key: list(value) for key, value in constraints.items()}
            compatible = True
            for dependency_id, dependency_constraint in sorted(manifest.requires_packs.items()):
                next_constraints.setdefault(dependency_id, []).append(dependency_constraint)
                dependency = next_selected.get(dependency_id)
                if dependency is not None and not version_satisfies(
                    industry_iq_manifest(dependency).version, dependency_constraint
                ):
                    compatible = False
                    break
            if not compatible:
                continue
            solved = self._solve(next_selected, next_constraints)
            if solved is not None:
                return solved
        return None

    def _install_order(self, selected: dict[str, IndustryIQPack]) -> list[str]:
        visiting: list[str] = []
        visited: set[str] = set()
        order: list[str] = []

        def visit(pack_id: str) -> None:
            if pack_id in visited:
                return
            if pack_id in visiting:
                cycle = visiting[visiting.index(pack_id) :] + [pack_id]
                raise IndustryIQResolutionError(
                    "PACK_DEPENDENCY_CYCLE",
                    "Industry IQ pack dependency cycle: " + " -> ".join(cycle),
                )
            visiting.append(pack_id)
            manifest = industry_iq_manifest(selected[pack_id])
            for dependency_id in sorted(manifest.requires_packs):
                if dependency_id not in selected:
                    raise IndustryIQResolutionError(
                        "PACK_DEPENDENCY_UNRESOLVED",
                        f"Resolved pack {pack_id} is missing dependency {dependency_id}",
                    )
                visit(dependency_id)
            visiting.pop()
            visited.add(pack_id)
            order.append(pack_id)

        for pack_id in sorted(selected):
            visit(pack_id)
        return order

    def _validate_capability_collisions(
        self,
        runtime: CEPIORuntime,
        manifests: Mapping[str, IndustryIQPackManifest],
    ) -> None:
        claimed: dict[tuple[str, str], str] = {}
        runtime_checks = {
            "function": runtime.has_function,
            "decision": runtime.has_decision,
            "action": runtime.has_action,
        }
        for pack_id in sorted(manifests):
            manifest = manifests[pack_id]
            capabilities = {
                "function": manifest.functions,
                "decision": manifest.decisions,
                "action": manifest.actions,
            }
            for kind, names in capabilities.items():
                for name in sorted(names):
                    key = (kind, name)
                    prior = claimed.get(key)
                    if prior is not None:
                        raise IndustryIQResolutionError(
                            "PACK_CAPABILITY_COLLISION",
                            f"Industry IQ packs {prior} and {pack_id} both claim {kind} {name}",
                        )
                    if runtime_checks[kind](name):
                        raise IndustryIQResolutionError(
                            "CORE_CAPABILITY_COLLISION",
                            f"Industry IQ pack {pack_id} attempts to replace Core {kind} {name}",
                        )
                    claimed[key] = pack_id


def install_industry_iq_packs(
    runtime: CEPIORuntime, packs: Iterable[IndustryIQPack]
) -> dict[str, str]:
    """Compatibility helper backed by the v0.5 registry/resolver.

    The supplied pack versions are pinned exactly, so existing callers keep deterministic
    behavior while gaining dependency, compatibility and collision validation.
    """

    materialized = list(packs)
    registry = IndustryIQPackRegistry()
    requested: dict[str, str] = {}
    for pack in materialized:
        registry.register(pack)
        requested[pack.pack_id] = f"=={pack.version}"
    registry.install(runtime, requested)
    return dict(runtime.industry_iq_packs)
