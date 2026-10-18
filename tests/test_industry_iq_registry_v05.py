from __future__ import annotations

import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_npt_iq import DRILLING_NPT_IQ_PACK
from cepio.industry_iq import (
    IndustryIQPackManifest,
    IndustryIQPackRegistry,
    IndustryIQResolutionError,
    industry_iq_manifest,
    install_industry_iq_packs,
    version_satisfies,
)


class DummyPack:
    def __init__(self, manifest: IndustryIQPackManifest) -> None:
        self.manifest = manifest
        self.pack_id = manifest.pack_id
        self.version = manifest.version

    def install(self, runtime) -> None:
        trace = list(getattr(runtime, "industry_iq_install_trace", []))
        trace.append(self.pack_id)
        setattr(runtime, "industry_iq_install_trace", trace)


class LegacyPack:
    pack_id = "cepio.iq.legacy"
    version = "1.0.0"

    def install(self, runtime) -> None:
        return None


class DictManifestPack:
    pack_id = "cepio.iq.dict"
    version = "1.0.0"
    manifest = {
        "pack_id": "cepio.iq.dict",
        "version": "1.0.0",
        "requires_core": ">=0.4.0,<1.0.0",
    }

    def install(self, runtime) -> None:
        return None


def test_version_constraints_are_deterministic():
    assert version_satisfies("1.2.3", ">=1.0.0,<2.0.0")
    assert version_satisfies("1.2.3", ">=1.0.0,,<2.0.0")
    assert version_satisfies("1.2.3", "^1.1.0")
    assert version_satisfies("0.2.5", "^0.2.1")
    assert version_satisfies("0.0.5", "^0.0.5")
    assert version_satisfies("1.2.9", "~1.2.3")
    assert version_satisfies("1.2.3", "=1.2.3")
    assert version_satisfies("1.2.3", "1.2.3")
    assert not version_satisfies("2.0.0", "^1.1.0")
    assert not version_satisfies("0.3.0", "^0.2.1")
    assert not version_satisfies("1.3.0", "~1.2.3")


def test_invalid_semver_is_rejected():
    with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
        version_satisfies("1.2", "*")


def test_manifest_supports_legacy_and_mapping_forms_but_rejects_identity_mismatch():
    legacy = industry_iq_manifest(LegacyPack())
    assert legacy.pack_id == "cepio.iq.legacy"
    assert legacy.requires_core == "*"

    mapped = industry_iq_manifest(DictManifestPack())
    assert mapped.pack_id == "cepio.iq.dict"
    assert mapped.requires_core == ">=0.4.0,<1.0.0"

    pack = DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.actual", version="1.0.0"))
    pack.pack_id = "cepio.iq.mismatch"
    with pytest.raises(ValueError, match="identity"):
        industry_iq_manifest(pack)


def test_registry_rejects_duplicate_pack_version_and_lists_manifests_deterministically():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    older = DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.0.0"))
    newer = DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.2.0"))
    other = DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.alpha", version="1.0.0"))
    registry.register(older)
    registry.register(newer)
    registry.register(other)

    assert [(item.pack_id, item.version) for item in registry.manifests()] == [
        ("cepio.iq.alpha", "1.0.0"),
        ("cepio.iq.shared", "1.2.0"),
        ("cepio.iq.shared", "1.0.0"),
    ]

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.register(DummyPack(older.manifest))
    assert exc.value.code == "PACK_VERSION_ALREADY_REGISTERED"


def test_registry_resolves_highest_compatible_transitive_dependency():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.0.0")))
    registry.register(DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.2.0")))
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.app",
                version="2.0.0",
                requires_core=">=0.4.0,<1.0.0",
                requires_packs={"cepio.iq.shared": ">=1.0.0,<2.0.0"},
            )
        )
    )

    resolution = registry.resolve({"cepio.iq.app": "==2.0.0"})

    assert resolution.selected == {
        "cepio.iq.app": "2.0.0",
        "cepio.iq.shared": "1.2.0",
    }
    assert resolution.install_order == ["cepio.iq.shared", "cepio.iq.app"]


def test_registry_composes_multiple_packs_on_one_shared_dependency():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.5.0")))
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.a",
                version="1.0.0",
                requires_packs={"cepio.iq.shared": ">=1.0.0,<2.0.0"},
            )
        )
    )
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.b",
                version="1.0.0",
                requires_packs={"cepio.iq.shared": "^1.2.0"},
            )
        )
    )

    resolution = registry.resolve(["cepio.iq.a", "cepio.iq.b"])

    assert resolution.selected["cepio.iq.shared"] == "1.5.0"
    assert resolution.install_order == ["cepio.iq.shared", "cepio.iq.a", "cepio.iq.b"]


def test_empty_request_resolves_to_empty_composition():
    registry = IndustryIQPackRegistry(core_version="0.4.0")

    resolution = registry.resolve([])

    assert resolution.selected == {}
    assert resolution.install_order == []


def test_invalid_request_identity_and_constraint_fail_before_resolution():
    registry = IndustryIQPackRegistry(core_version="0.4.0")

    with pytest.raises(ValueError, match="cannot be empty"):
        registry.resolve({"": "*"})
    with pytest.raises(ValueError, match="Invalid Industry IQ version constraint"):
        registry.resolve({"cepio.iq.missing": ">=bad"})


def test_missing_dependency_fails_closed():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.app",
                version="1.0.0",
                requires_packs={"cepio.iq.missing": "*"},
            )
        )
    )

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.resolve(["cepio.iq.app"])

    assert exc.value.code == "PACK_RESOLUTION_FAILED"


def test_selected_pack_constraint_conflict_fails_closed():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    pack = DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.0.0"))

    solved = registry._solve(
        {"cepio.iq.shared": pack},
        {"cepio.iq.shared": [">=2.0.0"]},
    )

    assert solved is None


def test_selected_dependency_conflict_backtracks_before_runtime_mutation():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    shared = DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.0shared", version="1.0.0"))
    app = DummyPack(
        IndustryIQPackManifest(
            pack_id="cepio.iq.app",
            version="1.0.0",
            requires_packs={"cepio.iq.0shared": ">=2.0.0"},
        )
    )
    registry.register(shared)
    registry.register(app)

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.resolve(
            {
                "cepio.iq.0shared": "==1.0.0",
                "cepio.iq.app": "==1.0.0",
            }
        )

    assert exc.value.code == "PACK_RESOLUTION_FAILED"


def test_incompatible_dependency_constraints_fail_closed():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="1.5.0")))
    registry.register(DummyPack(IndustryIQPackManifest(pack_id="cepio.iq.shared", version="2.1.0")))
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.a",
                version="1.0.0",
                requires_packs={"cepio.iq.shared": "<2.0.0"},
            )
        )
    )
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.b",
                version="1.0.0",
                requires_packs={"cepio.iq.shared": ">=2.0.0"},
            )
        )
    )

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.resolve(["cepio.iq.a", "cepio.iq.b"])

    assert exc.value.code == "PACK_RESOLUTION_FAILED"


def test_core_version_incompatibility_fails_closed():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.future",
                version="1.0.0",
                requires_core=">=0.5.0,<1.0.0",
            )
        )
    )

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.resolve(["cepio.iq.future"])

    assert exc.value.code == "PACK_RESOLUTION_FAILED"


def test_dependency_cycle_is_rejected_before_install():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.a",
                version="1.0.0",
                requires_packs={"cepio.iq.b": "*"},
            )
        )
    )
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.b",
                version="1.0.0",
                requires_packs={"cepio.iq.a": "*"},
            )
        )
    )

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.resolve(["cepio.iq.a"])

    assert exc.value.code == "PACK_DEPENDENCY_CYCLE"


def test_install_order_rejects_malformed_resolved_graph():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    app = DummyPack(
        IndustryIQPackManifest(
            pack_id="cepio.iq.app",
            version="1.0.0",
            requires_packs={"cepio.iq.missing": "*"},
        )
    )

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry._install_order({"cepio.iq.app": app})

    assert exc.value.code == "PACK_DEPENDENCY_UNRESOLVED"


def test_pack_cannot_replace_existing_core_capability():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.unsafe",
                version="1.0.0",
                functions={"calculateProductionLoss"},
            )
        )
    )
    runtime = build_runtime()

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.install(runtime, ["cepio.iq.unsafe"])

    assert exc.value.code == "CORE_CAPABILITY_COLLISION"
    assert runtime.industry_iq_packs == {}
    assert not hasattr(runtime, "industry_iq_install_trace")


def test_pack_capability_collision_is_rejected_before_install():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.a",
                version="1.0.0",
                functions={"sharedFunction"},
            )
        )
    )
    registry.register(
        DummyPack(
            IndustryIQPackManifest(
                pack_id="cepio.iq.b",
                version="1.0.0",
                functions={"sharedFunction"},
            )
        )
    )
    runtime = build_runtime()

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.install(runtime, ["cepio.iq.a", "cepio.iq.b"])

    assert exc.value.code == "PACK_CAPABILITY_COLLISION"
    assert runtime.industry_iq_packs == {}
    assert not hasattr(runtime, "industry_iq_install_trace")


def test_pack_cannot_be_installed_twice():
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(DRILLING_NPT_IQ_PACK)
    runtime = build_runtime()
    registry.install(runtime, ["cepio.iq.drilling.npt"])

    with pytest.raises(IndustryIQResolutionError) as exc:
        registry.install(runtime, ["cepio.iq.drilling.npt"])

    assert exc.value.code == "PACK_ALREADY_INSTALLED"


def test_drilling_pack_publishes_deployment_manifest_and_preserves_compatibility_helper():
    runtime = build_runtime()

    installed = install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])

    assert installed == {"cepio.iq.drilling.npt": "0.1.0"}
    deployment = runtime.industry_iq_deployment_manifest
    assert deployment.install_order == ["cepio.iq.drilling.npt"]
    manifest = deployment.packs["cepio.iq.drilling.npt"]
    assert manifest.requires_core == ">=0.4.0,<1.0.0"
    assert manifest.functions == {"calculateNPTDuration"}
    assert manifest.decisions == {"npt-follow-up-recommendation"}
    assert manifest.actions == {"CreateNPTInvestigation"}
