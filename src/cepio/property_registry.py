from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from cepio.modules import ModuleCatalogue


class UnknownPropertyError(KeyError):
    pass


class AmbiguousPropertyError(ValueError):
    pass


@dataclass(frozen=True)
class PropertyDefinition:
    qname: str
    iri: str
    datatype: str
    authority: str

    @property
    def local_name(self) -> str:
        return self.iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


class PropertyRegistry:
    """IRI-first registry for canonical CEPIO datatype properties.

    Canonical identity is the full RDF IRI. QNames are stable human/developer aliases.
    Local names are accepted only when unambiguous across all registered modules.
    """

    def __init__(self, properties: dict[str, PropertyDefinition]) -> None:
        self.properties = properties
        self.by_iri = {p.iri: p for p in properties.values()}
        if len(self.by_iri) != len(properties):
            raise ValueError("Canonical property IRIs must be unique")
        self.aliases: dict[str, set[str]] = {}
        for definition in properties.values():
            self._add_alias(definition.qname, definition.iri)
            self._add_alias(definition.local_name, definition.iri)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PropertyRegistry":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        props = {
            qname: PropertyDefinition(
                qname=qname,
                iri=spec["iri"],
                datatype=spec["datatype"],
                authority=spec.get("authority", "domain"),
            )
            for qname, spec in raw.get("properties", {}).items()
        }
        return cls(props)

    def resolve(self, value: str) -> PropertyDefinition:
        if value in self.by_iri:
            return self.by_iri[value]
        candidates = self.aliases.get(value, set())
        if not candidates:
            raise UnknownPropertyError(f"Unknown CEPIO canonical property: {value}")
        if len(candidates) > 1:
            raise AmbiguousPropertyError(
                f"Ambiguous CEPIO property alias '{value}'. Use a QName or full IRI. "
                f"Candidates: {sorted(candidates)}"
            )
        return self.by_iri[next(iter(candidates))]

    def canonical_iri(self, value: str) -> str:
        return self.resolve(value).iri

    def validate_against_catalogue(self, catalogue: "ModuleCatalogue") -> None:
        for definition in self.properties.values():
            catalogue.owning_module(definition.iri)

    def owning_module(self, value: str, catalogue: "ModuleCatalogue") -> str:
        return catalogue.owning_module(self.resolve(value).iri)

    def _add_alias(self, alias: str, iri: str) -> None:
        if alias:
            self.aliases.setdefault(alias, set()).add(iri)
