from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from rdflib import Graph

from ...modules import ModuleCatalogue
from ...profiles import ProfileManifest, ProfileRegistry
from .fabric_iq import (
    FabricBindingProfile,
    FabricIQBindingGenerator,
    FabricIQBindingManifest,
    load_fabric_binding_profile,
)


def load_profile_fabric_bindings(profiles: list[ProfileManifest]) -> FabricBindingProfile:
    entities = []
    relationships = []
    for profile in profiles:
        path = profile.binding_path("fabric_iq")
        if path is None:
            continue
        binding = load_fabric_binding_profile(path)
        entities.extend(binding.entity_bindings)
        relationships.extend(binding.relationship_bindings)
    return FabricBindingProfile(entity_bindings=entities, relationship_bindings=relationships)


def generate_profiled_fabric_bundle(
    root: str | Path,
    requested_modules: list[str],
    *,
    profile_ids: tuple[str, ...] | list[str] = (),
    source_bindings: FabricBindingProfile | None = None,
) -> tuple[str, FabricIQBindingManifest, dict[str, str]]:
    root = Path(root)
    catalogue = ModuleCatalogue.load(root / "ontology-modules.yaml")
    profiles = ProfileRegistry(root / "profiles", catalogue).load(profile_ids) if profile_ids else []
    effective_bindings = source_bindings or load_profile_fabric_bindings(profiles)
    generator = FabricIQBindingGenerator(root, catalogue=catalogue)
    canonical_ttl, manifest = generator.generate_bundle(requested_modules, source_bindings=effective_bindings)
    if not profiles:
        return canonical_ttl, manifest, {}
    graph = Graph()
    graph.parse(data=canonical_ttl, format="turtle")
    for profile in profiles:
        profile.add_ontology_to_graph(graph)
    ttl = generator._serialize_deterministic_turtle(graph, requested_modules, manifest.resolved_modules)
    manifest = manifest.model_copy(update={"ontology_artifact_sha256": sha256(ttl.encode("utf-8")).hexdigest()})
    return ttl, manifest, {profile.profile_id: profile.version for profile in profiles}
