from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PropertyDefinition:
    qname: str
    iri: str
    datatype: str
    authority: str


class PropertyRegistry:
    """Machine-readable registry for canonical CEPIO datatype properties."""

    def __init__(self, properties: dict[str, PropertyDefinition]) -> None:
        self.properties = properties
        self.by_iri = {p.iri: p for p in properties.values()}

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PropertyRegistry":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        props = {qname: PropertyDefinition(qname=qname, iri=spec["iri"], datatype=spec["datatype"], authority=spec.get("authority", "domain")) for qname, spec in raw.get("properties", {}).items()}
        if len({p.iri for p in props.values()}) != len(props):
            raise ValueError("Canonical property IRIs must be unique")
        return cls(props)

    def resolve(self, value: str) -> PropertyDefinition:
        if value in self.properties:
            return self.properties[value]
        if value in self.by_iri:
            return self.by_iri[value]
        raise KeyError(f"Unknown CEPIO canonical property: {value}")
