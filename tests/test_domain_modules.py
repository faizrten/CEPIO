import csv
from pathlib import Path

from rdflib import Graph

from cepio.registry import TypeRegistry

ROOT = Path(__file__).parents[1]


def _read_mapping(name: str):
    with (ROOT / "mappings" / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_profile_mapping(profile: str, name: str):
    with (ROOT / "profiles" / profile / "mappings" / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_normalized_domain_modules_parse_and_register():
    graph = Graph()
    for path in (ROOT / "ontologies").glob("*.ttl"):
        graph.parse(path, format="turtle")
    registry = TypeRegistry.from_ontology_dir(ROOT / "ontologies")
    for type_name in ["Site", "FailureMode", "ProcessSafetyEvent", "Scorecard", "CrewMember", "ProcessStream", "DesignTag", "OperatingRig", "Recommendation"]:
        assert type_name in registry.object_types


def test_reference_ontology_mappings_are_complete_without_customer_pollution():
    seo_canonical = _read_mapping("seo_to_cepio.csv")
    satorp = _read_profile_mapping("satorp", "seo_customer_to_cepio.csv")
    ad = _read_mapping("ad_to_cepio.csv")

    assert len(seo_canonical) == 41
    assert len(satorp) == 1
    assert len(seo_canonical) + len(satorp) == 42
    assert len(ad) == 59
    assert all(row["canonical_concept"] for row in seo_canonical)
    assert all(row["canonical_concept"] for row in satorp)
    assert all(row["canonical_concept"] for row in ad)
    assert all(row["promotion_level"] != "customer-profile" for row in seo_canonical)
    assert satorp[0]["source_concept"] == "AmiralAsset"


def test_shared_source_concepts_converge_to_same_cepio_types():
    seo = {row["source_concept"]: row for row in _read_mapping("seo_to_cepio.csv")}
    ad = {row["source_concept"]: row for row in _read_mapping("ad_to_cepio.csv")}
    for shared in ["WorkOrder", "FailureMode", "ProcessSafetyEvent", "SparePart"]:
        assert seo[shared]["canonical_concept"] == ad[shared]["canonical_concept"]
