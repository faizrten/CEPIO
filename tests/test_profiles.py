from __future__ import annotations

from pathlib import Path

import pytest

from cepio.bootstrap import build_runtime
from cepio.modules import ModuleCatalogue
from cepio.profiles import ProfileManifest, ProfileRegistry

ROOT = Path(__file__).parents[1]


def test_satorp_profile_manifest_validates_against_canonical_modules():
    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    profiles = ProfileRegistry(ROOT / "profiles", catalogue).load(["satorp"])
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.profile_id == "satorp"
    assert profile.version == "0.1.0"
    assert profile.namespace == "https://cepio.org/profile/satorp#"
    assert profile.binding_path("fabric_iq") == ROOT / "profiles" / "satorp" / "bindings" / "fabric-iq.yaml"


def test_runtime_loads_profile_ontology_only_when_selected():
    canonical = build_runtime(resource_root=ROOT)
    assert not canonical.type_registry.is_declared_type("https://cepio.org/profile/satorp#AmiralAsset")

    satorp = build_runtime(resource_root=ROOT, profiles=["satorp"])
    assert satorp.type_registry.is_declared_type("https://cepio.org/profile/satorp#AmiralAsset")
    assert satorp.type_registry.is_a(
        "https://cepio.org/profile/satorp#AmiralAsset",
        "https://cepio.org/ontology/asset#InstalledAsset",
    )
    assert satorp.profile_versions == {"satorp": "0.1.0"}


def test_unknown_profile_fails_closed():
    with pytest.raises(ValueError, match="Unknown CEPIO customer profile"):
        build_runtime(resource_root=ROOT, profiles=["does-not-exist"])


def test_profile_dependency_mismatch_fails(tmp_path):
    profile_root = tmp_path / "bad"
    profile_root.mkdir()
    (profile_root / "profile.yaml").write_text(
        """schema_version: '1'\nid: bad\nversion: 0.1.0\ndepends_on:\n  core: '>=99.0.0'\nfiles: {}\n"""
    )
    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    manifest = ProfileManifest.load(profile_root / "profile.yaml")
    with pytest.raises(ValueError, match="requires core"):
        manifest.validate_dependencies(catalogue)
