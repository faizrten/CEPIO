from pathlib import Path

from rdflib import Graph, OWL, RDF, URIRef

from cepio.integrations.microsoft.profile_fabric_iq import generate_profiled_fabric_bundle

ROOT = Path(__file__).parents[1]


def test_fabric_iq_bundle_layers_selected_profile_ontology():
    ttl, manifest, profiles = generate_profiled_fabric_bundle(
        ROOT,
        ["core", "industrial", "asset", "process_industry", "epcic"],
        profile_ids=["satorp"],
    )
    graph = Graph()
    graph.parse(data=ttl, format="turtle")
    amiral = URIRef("https://cepio.org/profile/satorp#AmiralAsset")
    assert (amiral, RDF.type, OWL.Class) in graph
    assert profiles == {"satorp": "0.1.0"}
    assert manifest.ontology_artifact_sha256


def test_fabric_iq_bundle_without_profile_is_canonical_only():
    ttl, _, profiles = generate_profiled_fabric_bundle(
        ROOT,
        ["core", "industrial", "asset"],
    )
    graph = Graph()
    graph.parse(data=ttl, format="turtle")
    assert URIRef("https://cepio.org/profile/satorp#AmiralAsset") not in set(graph.subjects())
    assert profiles == {}
