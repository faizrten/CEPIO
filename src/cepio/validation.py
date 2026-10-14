from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, RDF
from rdflib.namespace import SH


@dataclass
class ValidationReport:
    conforms: bool
    engine: str
    messages: list[str] = field(default_factory=list)


def validate_shacl(
    data_graph_path: str | Path,
    shapes_graph_path: str | Path,
    *,
    ontology_dir: str | Path | None = None,
) -> ValidationReport:
    try:
        from pyshacl import validate  # type: ignore

        ont_graph = Graph()
        if ontology_dir:
            for path in sorted(Path(ontology_dir).glob("*.ttl")):
                ont_graph.parse(path, format="turtle")
        conforms, _results_graph, results_text = validate(
            data_graph=str(data_graph_path),
            shacl_graph=str(shapes_graph_path),
            ont_graph=ont_graph if ontology_dir else None,
            inference="rdfs",
            abort_on_first=False,
        )
        return ValidationReport(conforms=bool(conforms), engine="pyshacl", messages=[] if conforms else [str(results_text)])
    except ImportError:
        return _validate_bootstrap_subset(data_graph_path, shapes_graph_path)


def _validate_bootstrap_subset(data_graph_path: str | Path, shapes_graph_path: str | Path) -> ValidationReport:
    data = Graph().parse(str(data_graph_path), format="turtle")
    shapes = Graph().parse(str(shapes_graph_path), format="turtle")
    messages: list[str] = []

    for shape in shapes.subjects(RDF.type, SH.NodeShape):
        for target_class in shapes.objects(shape, SH.targetClass):
            targets = list(data.subjects(RDF.type, target_class))
            for prop_shape in shapes.objects(shape, SH.property):
                path = next(iter(shapes.objects(prop_shape, SH.path)), None)
                min_count_literal = next(iter(shapes.objects(prop_shape, SH.minCount)), None)
                min_count = int(min_count_literal) if min_count_literal is not None else 0
                if path is None:
                    continue
                for node in targets:
                    count = sum(1 for _ in data.objects(node, path))
                    if count < min_count:
                        messages.append(f"{node} requires at least {min_count} value(s) for {path}; found {count}")
    return ValidationReport(conforms=not messages, engine="cepio-bootstrap-shacl-subset", messages=messages)
