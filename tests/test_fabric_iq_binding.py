from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef

from cepio.integrations.microsoft.fabric_iq import (
    FabricIQBindingGenerator,
    FabricSourceType,
    load_fabric_binding_profile,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "integrations/microsoft/fabric_iq/asset-work.bindings.yaml"
EQUIPMENT = "https://cepio.org/ontology/industrial#Equipment"
WORK_ORDER = "https://cepio.org/ontology/industrial#WorkOrder"
HAS_WORK_ORDER = "https://cepio.org/ontology/industrial#hasWorkOrder"
ASSET_TAG = "https://cepio.org/ontology/asset#assetTag"
SOURCE_ID = "https://cepio.org/ontology/core#sourceId"


def _version_tuple(value: object) -> tuple[int, ...]:
    return tuple(int(part) for part in str(value).split("."))


def _generate():
    generator = FabricIQBindingGenerator(ROOT)
    profile = load_fabric_binding_profile(PROFILE)
    ttl, manifest = generator.generate_bundle(
        ["asset", "work_management"],
        source_bindings=profile,
    )
    return generator, ttl, manifest


def test_asset_work_reference_binding_is_deterministic_and_versioned():
    generator, ttl, manifest = _generate()
    ttl_again, manifest_again = generator.generate_bundle(
        ["asset", "work_management"],
        source_bindings=load_fabric_binding_profile(PROFILE),
    )

    assert ttl == ttl_again
    assert manifest.to_json() == manifest_again.to_json()
    assert manifest.requested_modules == ["asset", "work_management"]
    assert set(manifest.resolved_modules) == {"core", "industrial", "asset", "work_management"}
    assert len(manifest.canonical_contract_sha256) == 64
    assert len(manifest.ontology_artifact_sha256) == 64

    modules = {module.module_id: module for module in manifest.modules}
    # Reference bindings require at least the semantic slice they were created
    # against; additive compatible module versions must not break the contract.
    assert _version_tuple(modules["asset"].version) >= (0, 1, 0)
    assert _version_tuple(modules["work_management"].version) >= (0, 1, 1)

    entities = {entity.canonical_iri: entity for entity in manifest.entity_types}
    assert EQUIPMENT in entities
    assert WORK_ORDER in entities
    assert ASSET_TAG in entities[EQUIPMENT].bound_properties
    assert SOURCE_ID in entities[WORK_ORDER].bound_properties

    properties = {prop.canonical_iri: prop for prop in manifest.datatype_properties}
    assert properties[ASSET_TAG].fabric_value_type == "string"
    assert properties[ASSET_TAG].bound_domains == [EQUIPMENT]
    assert properties[SOURCE_ID].bound_domains == [WORK_ORDER]

    relationships = {rel.canonical_iri: rel for rel in manifest.relationship_types}
    assert relationships[HAS_WORK_ORDER].domains == [EQUIPMENT]
    assert relationships[HAS_WORK_ORDER].ranges == [WORK_ORDER]


def test_reference_profile_uses_supported_fabric_source_kinds():
    profile = load_fabric_binding_profile(PROFILE)
    assert {binding.source_type for binding in profile.entity_bindings} == {
        FabricSourceType.lakehouse,
        FabricSourceType.warehouse,
    }
    assert profile.relationship_bindings[0].source_type == FabricSourceType.lakehouse


def test_generated_ttl_is_importable_turtle_and_round_trips_without_drift():
    generator, ttl, manifest = _generate()
    graph = Graph()
    graph.parse(data=ttl, format="turtle")

    assert (URIRef(EQUIPMENT), RDF.type, OWL.Class) in graph
    assert (URIRef(ASSET_TAG), RDF.type, OWL.DatatypeProperty) in graph
    assert (URIRef(ASSET_TAG), RDFS.domain, URIRef(EQUIPMENT)) in graph
    assert (URIRef(HAS_WORK_ORDER), RDF.type, OWL.ObjectProperty) in graph

    report = generator.validate_exported_ttl(ttl, manifest)
    assert report.conforms
    assert report.missing == []
    assert report.changed == []


def test_round_trip_validation_detects_missing_and_changed_semantics():
    generator, ttl, manifest = _generate()
    graph = Graph()
    graph.parse(data=ttl, format="turtle")

    graph.remove((URIRef(EQUIPMENT), RDF.type, OWL.Class))
    graph.remove((URIRef(HAS_WORK_ORDER), RDFS.range, URIRef(WORK_ORDER)))
    changed_ttl = graph.serialize(format="turtle")

    report = generator.validate_exported_ttl(changed_ttl, manifest)
    assert not report.conforms
    assert f"entity type missing: {EQUIPMENT}" in report.missing
    assert any(item.startswith(f"relationship ranges changed: {HAS_WORK_ORDER}") for item in report.changed)


def test_bundle_writer_outputs_import_and_manifest_files(tmp_path):
    generator = FabricIQBindingGenerator(ROOT)
    manifest = generator.write_bundle(
        tmp_path,
        ["asset", "work_management"],
        source_bindings=load_fabric_binding_profile(PROFILE),
    )

    ttl_path = tmp_path / "ontology.ttl"
    manifest_path = tmp_path / "binding-manifest.json"
    assert ttl_path.exists()
    assert manifest_path.exists()
    assert manifest.ontology_artifact_sha256 in manifest_path.read_text()
    assert "Microsoft Fabric IQ Ontology import artifact" in ttl_path.read_text()
