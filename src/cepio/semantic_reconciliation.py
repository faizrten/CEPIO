"""Deterministic lexical proposals against a host-approved ontology snapshot.

This is candidate discovery, not semantic equivalence, approval or promotion.
The caller supplies an authorized tenant-local envelope and trusted graph.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .platform_bindings import EvidenceEnvelope


@dataclass(frozen=True)
class ReconciliationProposal:
    source_key: str
    source_digest: str
    tenant_id: str
    ontology_digest: str
    term_digest: str
    candidates: tuple[str, ...]
    disposition: str
    blockers: tuple[str, ...]
    status: str = "proposal-only"


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def propose_reconciliation(
    envelope: EvidenceEnvelope, graph: Graph, *, tenant_id: str
) -> ReconciliationProposal:
    """Match exact normalized names/synonyms or exact IRIs, without mutation.

    All matching terms remain candidates. Units, context, rights and applicability
    require downstream qualification even when the lexical match is unique.
    No fuzzy matching, IRI minting, hierarchy inference or global promotion occurs.
    """
    if not tenant_id or envelope.reference.partition != tenant_id:
        raise PermissionError("Semantic evidence tenant mismatch")
    if (
        envelope.reference.record_kind != "semantic-term"
        or envelope.evidence.get("evidence_kind") != "semantic-metadata"
        or envelope.evidence.get("cepio_status") != "proposal-only"
    ):
        raise ValueError("Expected unapproved semantic-term evidence")
    term = envelope.evidence.get("term")
    if not isinstance(term, dict) or term.get("id") != envelope.reference.record_id:
        raise ValueError("Semantic term identity mismatch")
    name = term.get("name")
    synonyms = term.get("synonyms")
    if synonyms is None:
        synonyms = []
    if (
        not isinstance(name, str)
        or not name.strip()
        or not isinstance(synonyms, list)
        or any(not isinstance(item, str) for item in synonyms)
    ):
        raise ValueError("Term requires a name and string synonyms")
    # Only explicitly declared, named classes/properties participate. Blank-node
    # identities are unstable and are not legitimate mapping destinations.
    subjects = {
        s
        for kind in (OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property)
        for s in graph.subjects(RDF.type, kind)
        if isinstance(s, URIRef)
    }
    index: dict[str, set[str]] = {}
    snapshot = []
    for subject in sorted(subjects, key=str):
        iri = str(subject)
        labels = {iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]}
        for predicate in (RDFS.label, SKOS.prefLabel, SKOS.altLabel):
            labels.update(
                str(value)
                for value in graph.objects(subject, predicate)
                if isinstance(value, Literal) and value.language in (None, "en")
            )
        for label in labels:
            index.setdefault(_normalized(label), set()).add(iri)
        # Include definitions, units and relationships in the snapshot identifier,
        # not just labels. Graph serialization blank-node IDs are not canonical;
        # reject them here rather than promise reproducible snapshot digests.
    for triple in graph:
        if any(not isinstance(node, (URIRef, Literal)) for node in triple):
            raise ValueError("Use a named-node ontology projection for reconciliation")
        snapshot.append(tuple(node.n3() for node in triple))
    matches = set()
    iris = {str(subject) for subject in subjects}
    for value in [name, *synonyms]:
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
            if value in iris:
                matches.add(value)
        else:
            matches.update(index.get(_normalized(value), set()))
    candidates = tuple(sorted(matches))
    disposition = (
        "existing-candidate"
        if len(candidates) == 1
        else ("ambiguous" if candidates else "unmatched")
    )
    blockers = ["semantic-review-required", "units-context-and-rights-not-qualified"]
    if disposition == "ambiguous":
        blockers.append("multiple-canonical-candidates")
    if disposition == "unmatched":
        blockers.append("no-existing-concept-match")
    return ReconciliationProposal(
        source_key=envelope.reference.stable_key,
        source_digest=hashlib.sha256(
            json.dumps(envelope.reference.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest(),
        tenant_id=tenant_id,
        ontology_digest=hashlib.sha256(json.dumps(sorted(snapshot)).encode()).hexdigest(),
        term_digest=hashlib.sha256(json.dumps(term, sort_keys=True).encode()).hexdigest(),
        candidates=candidates,
        disposition=disposition,
        blockers=tuple(blockers),
    )
