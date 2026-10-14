from datetime import datetime, timezone
from pathlib import Path

from cepio.modules import ModuleCatalogue, compare_snapshots
from cepio.property_registry import PropertyRegistry
from cepio.provenance import (
    PropertyProvenance,
    SQLiteProvenanceRepository,
    SourceReference,
    TransformationRun,
    explain_property,
)

ROOT = Path(__file__).parents[1]


def test_property_contract_is_owned_by_versioned_modules():
    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    registry = PropertyRegistry.from_yaml(ROOT / "mappings/canonical_properties.yaml")
    registry.validate_against_catalogue(catalogue)
    assert registry.owning_module("asset:criticality", catalogue) == "asset"
    assert registry.resolve("asset:criticality").iri == "https://cepio.org/ontology/asset#criticality"
    assert registry.resolve("https://cepio.org/ontology/asset#criticality").qname == "asset:criticality"
    assert registry.resolve("criticality").qname == "asset:criticality"


def test_module_snapshot_includes_datatype_properties_and_detects_removal():
    catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
    snapshot = catalogue.snapshot(ROOT)
    assert "https://cepio.org/ontology/asset#criticality" in snapshot["modules"]["asset"]["datatype_properties"]
    changed = {**snapshot, "modules": {k: dict(v) for k, v in snapshot["modules"].items()}}
    changed["modules"]["asset"] = dict(changed["modules"]["asset"])
    changed["modules"]["asset"]["datatype_properties"] = [
        iri for iri in changed["modules"]["asset"]["datatype_properties"]
        if iri != "https://cepio.org/ontology/asset#criticality"
    ]
    diff = compare_snapshots(snapshot, changed)
    assert any("datatype property removed" in item and "criticality" in item for item in diff["breaking"])


def test_sqlite_property_provenance_survives_restart_and_is_explainable(tmp_path):
    registry = PropertyRegistry.from_yaml(ROOT / "mappings/canonical_properties.yaml")
    db = tmp_path / "provenance.db"
    transformation = TransformationRun(
        mapping_id="AD.EquipmentItem.conditionPct->asset:conditionPercent",
        mapping_version="1.0.0",
        code_version="test-sha",
        inputs={"source": "AD"},
    )
    repo = SQLiteProvenanceRepository(db)
    repo.add_transformation(transformation)
    record = PropertyProvenance.create(
        object_id="equipment-123",
        property_name="asset:conditionPercent",
        property_registry=registry,
        source=SourceReference(
            source_system="AD",
            source_entity="EquipmentItem",
            source_field="conditionPct",
            source_record_id="EQ-123",
        ),
        mapping_kind="canonical-property",
        mapping_version="1.0.0",
        observed_at=datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc),
        transformation_id=transformation.id,
        source_value=82,
    )
    repo.append_property(record)
    repo.close()

    reopened = SQLiteProvenanceRepository(db)
    explanation = explain_property("equipment-123", "asset:conditionPercent", registry, reopened)
    assert explanation["property"]["iri"] == "https://cepio.org/ontology/asset#conditionPercent"
    assert explanation["provenance"][0]["source"]["source_field"] == "conditionPct"
    assert explanation["provenance"][0]["source_value_hash"]
    assert transformation.id in explanation["transformations"]
    reopened.close()
