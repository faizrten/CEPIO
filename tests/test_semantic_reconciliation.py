from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from cepio.domain_bindings import ExternalRecordReference
from cepio.platform_bindings import EvidenceEnvelope
from cepio.semantic_reconciliation import propose_reconciliation


def evidence(name="Equipment", synonyms=None):
    return EvidenceEnvelope(
        reference=ExternalRecordReference(
            source_system="catalog",
            record_kind="semantic-term",
            record_id="t1",
            partition="tenant-a",
        ),
        evidence={
            "term": {"id": "t1", "name": name, "synonyms": synonyms},
            "evidence_kind": "semantic-metadata",
            "cepio_status": "proposal-only",
        },
    )


def graph():
    g = Graph()
    g.add((URIRef("urn:cepio#Equipment"), RDF.type, OWL.Class))
    return g


def reconcile(e=None, g=None):
    return propose_reconciliation(
        e if e is not None else evidence(), g if g is not None else graph(), tenant_id="tenant-a"
    )


def test_existing_candidate_remains_unapproved_and_graph_unchanged():
    g = graph()
    before = set(g)
    p = reconcile(evidence(" equipment "), g)
    assert p.candidates == ("urn:cepio#Equipment",)
    assert p.disposition == "existing-candidate"
    assert p.status == "proposal-only"
    assert "semantic-review-required" in p.blockers
    assert set(g) == before
    assert p == reconcile(evidence(" equipment "), g)


def test_ambiguity_across_namespaces_is_never_resolved_by_order():
    g = graph()
    g.add((URIRef("urn:other#Equipment"), RDF.type, OWL.Class))
    p = reconcile(g=g)
    assert p.disposition == "ambiguous"
    assert len(p.candidates) == 2
    assert "multiple-canonical-candidates" in p.blockers


def test_unknown_concept_does_not_mint_iri():
    p = reconcile(evidence("Unknown machinery"))
    assert p.candidates == ()
    assert p.disposition == "unmatched"


def test_synonyms_and_exact_iri_both_propose_existing_concept():
    assert reconcile(evidence("Machine", ["Equipment"])).candidates
    assert reconcile(evidence("urn:cepio#Equipment")).candidates


def test_conflicting_synonym_preserves_all_candidates():
    g = graph()
    g.add((URIRef("urn:cepio#Location"), RDF.type, OWL.Class))
    assert reconcile(evidence("Equipment", ["Location"]), g).disposition == "ambiguous"


def test_labels_language_and_snapshot_changes():
    g = graph()
    g.add((URIRef("urn:cepio#Equipment"), SKOS.altLabel, Literal("Machine", lang="en")))
    g.add((URIRef("urn:cepio#Equipment"), RDFS.label, Literal("Maschine", lang="de")))
    assert reconcile(evidence("Machine"), g).candidates
    assert not reconcile(evidence("Maschine"), g).candidates
    original = reconcile(g=g)
    g.add((URIRef("urn:cepio#Equipment"), RDFS.comment, Literal("New definition")))
    assert reconcile(g=g).ontology_digest != original.ontology_digest
    assert reconcile(evidence("Equipment", ["Machine"]), g).term_digest != original.term_digest


def test_actual_asset_ontology_existing_concept():
    g = Graph().parse(Path(__file__).resolve().parents[1] / "ontologies/asset.ttl")
    p = reconcile(evidence("FunctionalLocation"), g)
    assert p.candidates == ("https://cepio.org/ontology/asset#FunctionalLocation",)


def test_tenant_mismatch_denied():
    with pytest.raises(PermissionError):
        propose_reconciliation(evidence(), graph(), tenant_id="other")


@pytest.mark.parametrize(
    "field,value",
    [
        ("cepio_status", "approved"),
        ("evidence_kind", "measurement"),
        ("term", []),
        ("term", {"id": "wrong"}),
        ("term", {"id": "t1", "name": ""}),
        ("term", {"id": "t1", "name": "Equipment", "synonyms": "bad"}),
        ("term", {"id": "t1", "name": "Equipment", "synonyms": [3]}),
    ],
)
def test_invalid_evidence_rejected(field, value):
    e = evidence()
    e.evidence[field] = value
    with pytest.raises(ValueError):
        reconcile(e)


def test_blank_nodes_require_explicit_named_projection():
    g = graph()
    g.add((BNode(), RDF.type, OWL.Class))
    with pytest.raises(ValueError, match="named-node"):
        reconcile(g=g)
