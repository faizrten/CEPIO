"""Enforce concrete CEPIO boundaries and exercise the boundary detector itself."""

import ast
from pathlib import Path
import re

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/cepio"
CORE = {
    "model",
    "runtime",
    "policy",
    "contextual_policy",
    "registry",
    "property_registry",
    "repositories",
    "temporal",
    "provenance",
    "projection",
    "query",
    "query_backend",
    "contract_runtime",
    "modules",
    "functions",
}
SOURCE_NAMES = {"sap", "pi", "aveva", "osdu", "p6", "microsoft", "satorp", "seo"}


def imports(source):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""
            yield from (f"{node.module or ''}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "__import__")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
        ):
            if node.args and isinstance(node.args[0], ast.Constant):
                yield str(node.args[0].value)


def forbidden_core(source):
    return [
        name
        for name in imports(source)
        if set(re.split(r"[._]", name.lower()))
        & (SOURCE_NAMES | {"integrations", "adapters", "profiles"})
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import cepio.integrations.microsoft",
        "from .adapters import SAPAdapter",
        "from cepio import adapters",
        "__import__('sap')",
        "import cepio.sap_adapter",
        "importlib.import_module('cepio.integrations.sap')",
    ],
)
def test_detector_rejects_boundary_violations(source):
    assert forbidden_core(source)


def test_core_is_source_and_profile_neutral():
    paths = [SRC / f"{name}.py" for name in CORE] + list((SRC / "core").rglob("*.py"))
    for path in paths:
        assert not forbidden_core(path.read_text(encoding="utf-8")), path


def test_agents_access_enterprise_state_through_gateway():
    forbidden = {"adapters", "repositories", "runtime", "bootstrap", "external_actions", "kinetic"}
    for path in SRC.rglob("*agent*.py"):
        for name in imports(path.read_text(encoding="utf-8")):
            assert not set(name.split(".")) & forbidden, (path, name)


def test_external_write_dispatch_is_confined_to_governed_runtime():
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "write_governed"
            ):
                assert path.name == "external_actions.py", path


def test_profiles_do_not_redefine_canonical_semantics():
    defining = {
        RDF.type,
        RDFS.domain,
        RDFS.range,
        RDFS.subClassOf,
        RDFS.subPropertyOf,
        OWL.equivalentClass,
        OWL.equivalentProperty,
    }
    for manifest in (ROOT / "profiles").glob("*/profile.yaml"):
        raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        namespace = raw["namespace"]
        for relative in raw.get("files", {}).get("ontology", []):
            graph = Graph().parse(manifest.parent / relative)
            for subject, predicate, value in graph:
                if (
                    predicate == RDF.type
                    and value == OWL.Ontology
                    and str(subject) == namespace.rstrip("#/")
                ):
                    continue
                if predicate in defining and isinstance(subject, URIRef):
                    assert str(subject).startswith(namespace), (manifest, subject, predicate)
