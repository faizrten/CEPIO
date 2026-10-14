from pathlib import Path

from cepio.validation import validate_shacl

ROOT = Path(__file__).parents[1]


def test_reference_graph_conforms_to_shacl():
    report = validate_shacl(
        ROOT / "examples" / "satorp_hydrocracker.ttl",
        ROOT / "shapes" / "core.shacl.ttl",
        ontology_dir=ROOT / "ontologies",
    )
    assert report.conforms, report.messages
