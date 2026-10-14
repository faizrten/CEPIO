from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from rdflib import Graph, OWL, RDF, RDFS, URIRef

from ...modules import ModuleCatalogue


class FabricSourceType(str, Enum):
    lakehouse = "lakehouse"
    eventhouse = "eventhouse"
    kql_database = "kql_database"
    warehouse = "warehouse"
    sql_database = "sql_database"
    mirrored_database = "mirrored_database"
    semantic_model = "semantic_model"


class FabricEntitySourceBinding(BaseModel):
    entity_iri: str
    mode: Literal["static", "time_series"] = "static"
    source_type: FabricSourceType
    workspace_id: str | None = None
    item_id: str | None = None
    source_name: str | None = None
    schema_name: str | None = None
    table_name: str | None = None
    entity_key: list[str] = Field(default_factory=list)
    timestamp_column: str | None = None
    property_map: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_binding(self) -> "FabricEntitySourceBinding":
        if self.mode == "static" and not self.entity_key:
            raise ValueError("Static Fabric ontology bindings require at least one entity_key property")
        if self.mode == "time_series" and not self.timestamp_column:
            raise ValueError("Time-series Fabric ontology bindings require timestamp_column")
        return self


class FabricRelationshipSourceBinding(BaseModel):
    relationship_iri: str
    source_type: FabricSourceType
    workspace_id: str | None = None
    item_id: str | None = None
    source_name: str | None = None
    schema_name: str | None = None
    table_name: str | None = None
    source_key_map: dict[str, str] = Field(default_factory=dict)
    target_key_map: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_binding(self) -> "FabricRelationshipSourceBinding":
        if not self.source_key_map or not self.target_key_map:
            raise ValueError("Relationship bindings require source_key_map and target_key_map")
        return self


class FabricBindingProfile(BaseModel):
    schema_version: str = "0.1"
    entity_bindings: list[FabricEntitySourceBinding] = Field(default_factory=list)
    relationship_bindings: list[FabricRelationshipSourceBinding] = Field(default_factory=list)


class ModuleBindingMetadata(BaseModel):
    module_id: str
    namespace: str
    version: str
    tier: str
    stability: str


class FabricEntityType(BaseModel):
    canonical_iri: str
    name: str
    module_id: str
    module_version: str
    parents: list[str] = Field(default_factory=list)
    bound_properties: list[str] = Field(default_factory=list)


class FabricDatatypeProperty(BaseModel):
    canonical_iri: str
    name: str
    module_id: str
    module_version: str
    xsd_range: str | None = None
    fabric_value_type: str = "unknown"
    bound_domains: list[str] = Field(default_factory=list)


class FabricRelationshipType(BaseModel):
    canonical_iri: str
    name: str
    module_id: str
    module_version: str
    domains: list[str] = Field(default_factory=list)
    ranges: list[str] = Field(default_factory=list)


class FabricGraphProjection(BaseModel):
    mode: Literal["ontology_managed"] = "ontology_managed"
    eligible_static_source_types: list[str] = Field(
        default_factory=lambda: ["lakehouse", "mirrored_database"]
    )
    note: str = (
        "Fabric Graph eligibility is narrower than Ontology data-binding support; "
        "validate deployed source types before materialization."
    )


class FabricIQBindingManifest(BaseModel):
    schema_version: str = "0.1"
    target: str = "microsoft-fabric-iq-ontology-preview"
    artifact_format: str = "turtle"
    requested_modules: list[str]
    resolved_modules: list[str]
    modules: list[ModuleBindingMetadata]
    entity_types: list[FabricEntityType]
    datatype_properties: list[FabricDatatypeProperty]
    relationship_types: list[FabricRelationshipType]
    source_bindings: FabricBindingProfile
    graph_projection: FabricGraphProjection = Field(default_factory=FabricGraphProjection)
    canonical_contract_sha256: str
    ontology_artifact_sha256: str

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class FabricIQDriftReport(BaseModel):
    conforms: bool
    missing: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)
    additional: list[str] = Field(default_factory=list)


_XSD_TO_FABRIC = {
    "http://www.w3.org/2001/XMLSchema#string": "string",
    "http://www.w3.org/2001/XMLSchema#boolean": "boolean",
    "http://www.w3.org/2001/XMLSchema#dateTime": "datetime",
    "http://www.w3.org/2001/XMLSchema#date": "datetime",
    "http://www.w3.org/2001/XMLSchema#double": "double",
    "http://www.w3.org/2001/XMLSchema#float": "double",
    "http://www.w3.org/2001/XMLSchema#decimal": "double",
    "http://www.w3.org/2001/XMLSchema#integer": "integer",
    "http://www.w3.org/2001/XMLSchema#int": "integer",
    "http://www.w3.org/2001/XMLSchema#long": "integer",
}


def _local_name(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted(set(values))


def load_fabric_binding_profile(path: str | Path) -> FabricBindingProfile:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    return FabricBindingProfile.model_validate(raw)


class FabricIQBindingGenerator:
    """Generate a deterministic Fabric IQ binding from the canonical CEPIO contract.

    CEPIO remains authoritative. The emitted TTL is a deployment artifact for Fabric
    Ontology import, while the JSON manifest preserves CEPIO identity/version and
    Fabric-specific binding metadata that should not be written into CEPIO-Core.
    """

    def __init__(self, root: str | Path, catalogue: ModuleCatalogue | None = None) -> None:
        self.root = Path(root)
        self.catalogue = catalogue or ModuleCatalogue.load(self.root / "ontology-modules.yaml")

    def resolve_modules(self, requested_modules: list[str]) -> list[str]:
        unknown = sorted(set(requested_modules) - set(self.catalogue.modules))
        if unknown:
            raise ValueError(f"Unknown CEPIO modules requested for Fabric binding: {unknown}")
        required: set[str] = set()

        def visit(module_id: str) -> None:
            if module_id in required:
                return
            for dependency in self.catalogue.modules[module_id].dependencies:
                visit(dependency.module)
            required.add(module_id)

        for module_id in requested_modules:
            visit(module_id)
        return [m for m in self.catalogue.topological_order() if m in required]

    def generate_bundle(
        self,
        requested_modules: list[str],
        *,
        source_bindings: FabricBindingProfile | None = None,
    ) -> tuple[str, FabricIQBindingManifest]:
        profile = source_bindings or FabricBindingProfile()
        resolved = self.resolve_modules(requested_modules)
        graph = self._build_graph(resolved, profile)
        ttl = self._serialize_deterministic_turtle(graph, requested_modules, resolved)
        manifest = self._build_manifest(
            graph,
            requested_modules=requested_modules,
            resolved_modules=resolved,
            profile=profile,
            ontology_sha=sha256(ttl.encode("utf-8")).hexdigest(),
        )
        self._validate_profile(manifest)
        return ttl, manifest

    def write_bundle(
        self,
        output_dir: str | Path,
        requested_modules: list[str],
        *,
        source_bindings: FabricBindingProfile | None = None,
    ) -> FabricIQBindingManifest:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        ttl, manifest = self.generate_bundle(requested_modules, source_bindings=source_bindings)
        (output / "ontology.ttl").write_text(ttl)
        (output / "binding-manifest.json").write_text(manifest.to_json())
        return manifest

    def validate_exported_ttl(
        self,
        exported_ttl: str,
        manifest: FabricIQBindingManifest,
    ) -> FabricIQDriftReport:
        actual = Graph()
        actual.parse(data=exported_ttl, format="turtle")
        missing: list[str] = []
        changed: list[str] = []
        additional: list[str] = []

        expected_classes = {e.canonical_iri: e for e in manifest.entity_types}
        actual_classes = {str(s) for s in actual.subjects(RDF.type, OWL.Class)}
        for iri in sorted(set(expected_classes) - actual_classes):
            missing.append(f"entity type missing: {iri}")
        for iri in sorted(actual_classes - set(expected_classes)):
            additional.append(f"entity type additional: {iri}")
        for iri, expected in sorted(expected_classes.items()):
            if iri not in actual_classes:
                continue
            parents = _sorted_unique(str(o) for o in actual.objects(URIRef(iri), RDFS.subClassOf))
            if parents != expected.parents:
                changed.append(f"entity parents changed: {iri}: expected={expected.parents} actual={parents}")

        expected_properties = {p.canonical_iri: p for p in manifest.datatype_properties}
        actual_properties = {str(s) for s in actual.subjects(RDF.type, OWL.DatatypeProperty)}
        for iri in sorted(set(expected_properties) - actual_properties):
            missing.append(f"datatype property missing: {iri}")
        for iri in sorted(actual_properties - set(expected_properties)):
            additional.append(f"datatype property additional: {iri}")
        for iri, expected in sorted(expected_properties.items()):
            if iri not in actual_properties:
                continue
            ranges = _sorted_unique(str(o) for o in actual.objects(URIRef(iri), RDFS.range))
            expected_ranges = [expected.xsd_range] if expected.xsd_range else []
            if ranges != expected_ranges:
                changed.append(f"datatype range changed: {iri}: expected={expected_ranges} actual={ranges}")
            domains = _sorted_unique(str(o) for o in actual.objects(URIRef(iri), RDFS.domain))
            if domains != expected.bound_domains:
                changed.append(f"datatype domains changed: {iri}: expected={expected.bound_domains} actual={domains}")

        expected_relationships = {r.canonical_iri: r for r in manifest.relationship_types}
        actual_relationships = {str(s) for s in actual.subjects(RDF.type, OWL.ObjectProperty)}
        for iri in sorted(set(expected_relationships) - actual_relationships):
            missing.append(f"relationship type missing: {iri}")
        for iri in sorted(actual_relationships - set(expected_relationships)):
            additional.append(f"relationship type additional: {iri}")
        for iri, expected in sorted(expected_relationships.items()):
            if iri not in actual_relationships:
                continue
            domains = _sorted_unique(str(o) for o in actual.objects(URIRef(iri), RDFS.domain))
            ranges = _sorted_unique(str(o) for o in actual.objects(URIRef(iri), RDFS.range))
            if domains != expected.domains:
                changed.append(f"relationship domains changed: {iri}: expected={expected.domains} actual={domains}")
            if ranges != expected.ranges:
                changed.append(f"relationship ranges changed: {iri}: expected={expected.ranges} actual={ranges}")

        return FabricIQDriftReport(
            conforms=not missing and not changed,
            missing=missing,
            changed=changed,
            additional=additional,
        )

    def _build_graph(self, resolved_modules: list[str], profile: FabricBindingProfile) -> Graph:
        graph = Graph()
        for module_id in resolved_modules:
            graph.parse(self.root / self.catalogue.modules[module_id].file, format="turtle")

        contract = Graph()
        for contract_file in self.catalogue.contract_files:
            contract.parse(self.root / contract_file, format="turtle")
        resolved_set = set(resolved_modules)
        for subject in contract.subjects(RDF.type, OWL.DatatypeProperty):
            iri = str(subject)
            try:
                owner = self.catalogue.owning_module(iri)
            except ValueError:
                continue
            if owner not in resolved_set:
                continue
            for predicate, obj in contract.predicate_objects(subject):
                graph.add((subject, predicate, obj))

        # Canonical CEPIO properties intentionally remain reusable and mostly
        # domain-neutral. A Fabric deployment profile materializes property domains
        # only for explicitly bound entity types; CEPIO-Core is not modified.
        for binding in profile.entity_bindings:
            for property_iri in binding.property_map:
                graph.add((URIRef(property_iri), RDFS.domain, URIRef(binding.entity_iri)))
        return graph

    def _build_manifest(
        self,
        graph: Graph,
        *,
        requested_modules: list[str],
        resolved_modules: list[str],
        profile: FabricBindingProfile,
        ontology_sha: str,
    ) -> FabricIQBindingManifest:
        module_meta = [
            ModuleBindingMetadata(
                module_id=module_id,
                namespace=self.catalogue.modules[module_id].namespace,
                version=self.catalogue.modules[module_id].version,
                tier=self.catalogue.modules[module_id].tier,
                stability=self.catalogue.modules[module_id].stability,
            )
            for module_id in resolved_modules
        ]
        entities: list[FabricEntityType] = []
        bound_by_entity: dict[str, set[str]] = {}
        for binding in profile.entity_bindings:
            bound_by_entity.setdefault(binding.entity_iri, set()).update(binding.property_map)
        for subject in sorted({str(s) for s in graph.subjects(RDF.type, OWL.Class)}):
            owner = self._owner_in_resolved(subject, resolved_modules)
            if owner is None:
                continue
            mod = self.catalogue.modules[owner]
            entities.append(
                FabricEntityType(
                    canonical_iri=subject,
                    name=_local_name(subject),
                    module_id=owner,
                    module_version=mod.version,
                    parents=_sorted_unique(str(o) for o in graph.objects(URIRef(subject), RDFS.subClassOf)),
                    bound_properties=sorted(bound_by_entity.get(subject, set())),
                )
            )

        properties: list[FabricDatatypeProperty] = []
        for subject in sorted({str(s) for s in graph.subjects(RDF.type, OWL.DatatypeProperty)}):
            owner = self._owner_in_resolved(subject, resolved_modules)
            if owner is None:
                continue
            mod = self.catalogue.modules[owner]
            ranges = _sorted_unique(str(o) for o in graph.objects(URIRef(subject), RDFS.range))
            domains = _sorted_unique(str(o) for o in graph.objects(URIRef(subject), RDFS.domain))
            xsd_range = ranges[0] if len(ranges) == 1 else None
            properties.append(
                FabricDatatypeProperty(
                    canonical_iri=subject,
                    name=_local_name(subject),
                    module_id=owner,
                    module_version=mod.version,
                    xsd_range=xsd_range,
                    fabric_value_type=_XSD_TO_FABRIC.get(xsd_range or "", "unknown"),
                    bound_domains=domains,
                )
            )

        relationships: list[FabricRelationshipType] = []
        for subject in sorted({str(s) for s in graph.subjects(RDF.type, OWL.ObjectProperty)}):
            owner = self._owner_in_resolved(subject, resolved_modules)
            if owner is None:
                continue
            mod = self.catalogue.modules[owner]
            relationships.append(
                FabricRelationshipType(
                    canonical_iri=subject,
                    name=_local_name(subject),
                    module_id=owner,
                    module_version=mod.version,
                    domains=_sorted_unique(str(o) for o in graph.objects(URIRef(subject), RDFS.domain)),
                    ranges=_sorted_unique(str(o) for o in graph.objects(URIRef(subject), RDFS.range)),
                )
            )

        return FabricIQBindingManifest(
            requested_modules=list(requested_modules),
            resolved_modules=list(resolved_modules),
            modules=module_meta,
            entity_types=entities,
            datatype_properties=properties,
            relationship_types=relationships,
            source_bindings=profile,
            canonical_contract_sha256=self._canonical_contract_hash(resolved_modules),
            ontology_artifact_sha256=ontology_sha,
        )

    def _validate_profile(self, manifest: FabricIQBindingManifest) -> None:
        entities = {e.canonical_iri for e in manifest.entity_types}
        properties = {p.canonical_iri: p for p in manifest.datatype_properties}
        relationships = {r.canonical_iri for r in manifest.relationship_types}
        for binding in manifest.source_bindings.entity_bindings:
            if binding.entity_iri not in entities:
                raise ValueError(f"Fabric binding targets unknown CEPIO entity: {binding.entity_iri}")
            for prop in list(binding.entity_key) + list(binding.property_map):
                if prop not in properties:
                    raise ValueError(f"Fabric binding targets unknown CEPIO property: {prop}")
            for prop in binding.entity_key:
                if properties[prop].fabric_value_type not in {"string", "integer"}:
                    raise ValueError(
                        f"Fabric entity key must resolve to string/integer property: {prop} -> "
                        f"{properties[prop].fabric_value_type}"
                    )
        for binding in manifest.source_bindings.relationship_bindings:
            if binding.relationship_iri not in relationships:
                raise ValueError(
                    f"Fabric relationship binding targets unknown CEPIO relationship: {binding.relationship_iri}"
                )

    def _owner_in_resolved(self, iri: str, resolved_modules: list[str]) -> str | None:
        try:
            owner = self.catalogue.owning_module(iri)
        except ValueError:
            return None
        return owner if owner in set(resolved_modules) else None

    def _canonical_contract_hash(self, resolved_modules: list[str]) -> str:
        digest = sha256()
        for module_id in resolved_modules:
            mod = self.catalogue.modules[module_id]
            digest.update(module_id.encode("utf-8"))
            digest.update(mod.version.encode("utf-8"))
            digest.update((self.root / mod.file).read_bytes())
        for contract_file in sorted(self.catalogue.contract_files):
            digest.update(contract_file.encode("utf-8"))
            digest.update((self.root / contract_file).read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _serialize_deterministic_turtle(
        graph: Graph,
        requested_modules: list[str],
        resolved_modules: list[str],
    ) -> str:
        # N-Triples syntax is a valid subset of Turtle and avoids serializer ordering
        # differences across rdflib versions. The header remains human-readable.
        triples = sorted(
            f"{subject.n3()} {predicate.n3()} {obj.n3()} ."
            for subject, predicate, obj in graph
        )
        header = [
            "# CEPIO -> Microsoft Fabric IQ Ontology import artifact",
            "# Generated deterministically from the canonical CEPIO contract.",
            f"# Requested modules: {', '.join(requested_modules)}",
            f"# Resolved modules: {', '.join(resolved_modules)}",
            "# CEPIO remains the semantic source of truth; this file is a platform binding.",
            "",
        ]
        return "\n".join(header + triples) + "\n"
