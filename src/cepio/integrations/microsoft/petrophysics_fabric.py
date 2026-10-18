"""Microsoft Fabric evidence provider for CEPIO Petrophysics v1.1.

The provider converts normalized Fabric table rows into the provider-neutral
logical evidence packages consumed by the qualified Petrophysics runtimes.
Fabric is therefore a replaceable evidence implementation, not the owner of
CEPIO Petrophysics semantics.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

import yaml

from ...petrophysics_evidence import EvidenceProviderCapabilityError


@runtime_checkable
class FabricTableReader(Protocol):
    """Transport contract for normalized Fabric table reads.

    A production implementation may use a Fabric SQL endpoint, Warehouse,
    Lakehouse SQL analytics endpoint or another governed Fabric access path.
    """

    def read_rows(
        self,
        table_name: str,
        *,
        filters: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...


class InMemoryFabricTableReader:
    """Deterministic Fabric-shaped row reader for parity/regression tests."""

    def __init__(self, tables: Mapping[str, list[Mapping[str, Any]]]) -> None:
        self._tables = {
            name: [deepcopy(dict(row)) for row in rows] for name, rows in tables.items()
        }

    @classmethod
    def from_yaml(cls, path: str | Path) -> "InMemoryFabricTableReader":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("tables"), dict):
            raise ValueError("Fabric table fixture must contain a tables mapping")
        return cls(payload["tables"])

    def read_rows(
        self,
        table_name: str,
        *,
        filters: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._tables.get(table_name, [])
        predicates = dict(filters or {})
        return [
            deepcopy(row)
            for row in rows
            if all(row.get(key) == value for key, value in predicates.items())
        ]


class FabricPetrophysicsEvidenceProvider:
    """Resolve PET-02/PET-05/PET-06 from normalized Fabric-style tables."""

    _REQUIRED_TABLES = {
        "contexts",
        "formation_evaluation_cases",
        "external_evidence",
        "uncertainty_assessments",
        "confidence_assessments",
        "downstream_dependencies",
        "well_interpretations",
        "pet05_profile",
        "pet05_impacts",
        "pet06_handover",
        "pet06_transformations",
        "pet06_stale_dependencies",
    }

    def __init__(
        self,
        reader: FabricTableReader,
        binding: str | Path | Mapping[str, Any],
    ) -> None:
        self.reader = reader
        if isinstance(binding, (str, Path)):
            loaded = yaml.safe_load(Path(binding).read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("Fabric Petrophysics binding must be a YAML mapping")
            raw = loaded
        else:
            raw = deepcopy(dict(binding))
        self.binding = raw
        tables = raw.get("tables") or {}
        missing = sorted(self._REQUIRED_TABLES - set(tables))
        if missing:
            raise ValueError(f"Fabric Petrophysics binding missing tables: {missing}")
        self.tables: dict[str, str] = {str(k): str(v) for k, v in tables.items()}

    @property
    def provider_id(self) -> str:
        return str(self.binding.get("provider_id", "microsoft.fabric.petrophysics-v1"))

    @property
    def supported_journeys(self) -> frozenset[str]:
        return frozenset({"PET-02", "PET-05", "PET-06"})

    def resolve_pet02(self, *, well: str, interval: str) -> dict[str, Any]:
        context = self._one(
            "contexts",
            filters={"context_id": "PET-02", "well": well, "interval": interval},
            description=f"PET-02 context {well}/{interval}",
        )
        cases = self._rows(
            "formation_evaluation_cases", filters={"well": well, "interval": interval}
        )
        if not cases:
            raise EvidenceProviderCapabilityError(
                f"Fabric provider found no formation-evaluation cases for {well}/{interval}."
            )

        return {
            "id": context["benchmark_id"],
            "version": str(context.get("version", "1.1")),
            "synthetic": _as_bool(context.get("synthetic", False)),
            "provenance": {
                "origin": context.get("origin", "Microsoft Fabric evidence binding"),
                "source_dataset": context.get("source_dataset"),
                "fictional_identifiers": _as_bool(context.get("fictional_identifiers", False)),
                "intended_use": context.get("intended_use"),
            },
            "field": context.get("field"),
            "reservoir": context.get("reservoir"),
            "well": well,
            "interval": interval,
            "formation_evaluation_cases": [self._pet02_case(row) for row in cases],
            "external_evidence": [
                self._pet02_evidence(row)
                for row in self._rows(
                    "external_evidence", filters={"well": well, "interval": interval}
                )
            ],
            "uncertainty_assessments": [
                self._pet02_uncertainty(row)
                for row in self._rows(
                    "uncertainty_assessments", filters={"well": well, "interval": interval}
                )
            ],
            "confidence_assessments": [
                {
                    "id": row["id"],
                    "assesses": row["assesses"],
                    "rating": row["rating"],
                    "rationale": row.get("rationale", ""),
                }
                for row in self._rows(
                    "confidence_assessments", filters={"well": well, "interval": interval}
                )
            ],
            "downstream_dependencies": [
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "depends_on": _jsonish(row.get("depends_on_json"), default=[]),
                }
                for row in self._rows(
                    "downstream_dependencies", filters={"well": well, "interval": interval}
                )
            ],
        }

    def resolve_v1_portfolio(self) -> dict[str, Any]:
        context = self._one(
            "contexts",
            filters={"context_id": "PET-v1"},
            description="Petrophysics v1 portfolio context",
        )
        well_rows = self._rows("well_interpretations", filters={"reservoir": context["reservoir"]})
        wells = {
            str(row["well"]): {
                "authority_case": row["authority_case"],
                "method": row["method"],
                "rw_ohm_m": row.get("rw_ohm_m"),
                "archie_m": row.get("archie_m"),
                "archie_n": row.get("archie_n"),
                "porosity_cutoff_fraction": row["porosity_cutoff_fraction"],
                "sw_cutoff_fraction": row["sw_cutoff_fraction"],
                "phie_fraction": row.get("phie_fraction"),
                "sw_fraction": row.get("sw_fraction"),
                "net_pay_m": row.get("net_pay_m"),
                "contact_tvdss_m": row.get("contact_tvdss_m"),
                "permeability_transform": row["permeability_transform"],
            }
            for row in well_rows
        }
        profile_row = self._one(
            "pet05_profile",
            filters={"profile_id": "R3-Zone-B"},
            description="PET-05 canonical profile",
        )
        impact_targets = {
            str(row["well"]): list(_jsonish(row.get("impact_targets_json"), default=[]))
            for row in self._rows("pet05_impacts")
        }
        handover_row = self._one(
            "pet06_handover",
            filters={"handover_id": "R3-SM18"},
            description="PET-06 handover",
        )

        return {
            "id": context["benchmark_id"],
            "version": str(context.get("version", "1.1")),
            "synthetic": _as_bool(context.get("synthetic", False)),
            "provenance": {
                "origin": context.get("origin", "Microsoft Fabric evidence binding"),
                "source_dataset": context.get("source_dataset"),
                "fictional_identifiers": _as_bool(context.get("fictional_identifiers", False)),
            },
            "asset": {
                "field": context.get("field"),
                "reservoir": context.get("reservoir"),
                "equivalent_interval": context.get("equivalent_interval"),
            },
            "wells": wells,
            "PET-05": {
                "canonical_profile": {
                    "method": profile_row["method"],
                    "rw_range_ohm_m": [profile_row["rw_min"], profile_row["rw_max"]],
                    "porosity_cutoff_range_fraction": [
                        profile_row["porosity_cutoff_min"],
                        profile_row["porosity_cutoff_max"],
                    ],
                    "sw_cutoff_range_fraction": [
                        profile_row["sw_cutoff_min"],
                        profile_row["sw_cutoff_max"],
                    ],
                    "accepted_transforms": list(
                        _jsonish(profile_row.get("accepted_transforms_json"), default=[])
                    ),
                },
                "impact_targets": impact_targets,
            },
            "PET-06": {
                "authoritative_handover": {
                    "source_case": handover_row["source_case"],
                    "source_properties": dict(
                        _jsonish(handover_row.get("source_properties_json"), default={})
                    ),
                    "transformations": [
                        {
                            "id": row["id"],
                            "property": row["property"],
                            "from": _jsonish(row.get("from_value_json")),
                            "to": _jsonish(row.get("to_value_json")),
                            "method": row["method"],
                        }
                        for row in self._rows(
                            "pet06_transformations",
                            filters={"handover_id": handover_row["handover_id"]},
                        )
                    ],
                    "downstream_chain": list(
                        _jsonish(handover_row.get("downstream_chain_json"), default=[])
                    ),
                },
                "stale_dependencies": [
                    {
                        "well": row["well"],
                        "source_case": row["source_case"],
                        "current_transform": row["current_transform"],
                        "consumed_transform": row["consumed_transform"],
                        "consumer": row["consumer"],
                    }
                    for row in self._rows("pet06_stale_dependencies")
                ],
            },
        }

    def _rows(
        self,
        logical_table: str,
        *,
        filters: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self.reader.read_rows(self.tables[logical_table], filters=filters)

    def _one(
        self,
        logical_table: str,
        *,
        filters: Mapping[str, Any],
        description: str,
    ) -> dict[str, Any]:
        rows = self._rows(logical_table, filters=filters)
        if len(rows) != 1:
            raise EvidenceProviderCapabilityError(f"Expected one {description}; found {len(rows)}.")
        return rows[0]

    @staticmethod
    def _pet02_case(row: Mapping[str, Any]) -> dict[str, Any]:
        interpretation_ref = {
            "source_system": row["source_system"],
            "source_service": row["source_service"],
            "record_kind": row["record_kind"],
            "record_id": row["record_id"],
            "record_version": str(row["record_version"]),
        }
        if row.get("partition") is not None:
            interpretation_ref["partition"] = row["partition"]
        case = {
            "id": row["case_id"],
            "type": row.get(
                "type", "https://cepio.org/ontology/subsurface#FormationEvaluationCase"
            ),
            "state": row["state"],
            "interpretation_ref": interpretation_ref,
            "findings": dict(_jsonish(row.get("findings_json"), default={})),
            "assumptions": dict(_jsonish(row.get("assumptions_json"), default={})),
        }
        if row.get("supersedes"):
            case["supersedes"] = row["supersedes"]
        return case

    @staticmethod
    def _pet02_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
        source_ref = {
            "source_system": row["source_system"],
            "source_service": row["source_service"],
            "record_kind": row["record_kind"],
            "record_id": row["record_id"],
            "record_version": str(row["record_version"]),
        }
        if row.get("partition") is not None:
            source_ref["partition"] = row["partition"]
        item: dict[str, Any] = {
            "id": row["id"],
            "role": row["role"],
            "description": row.get("description", ""),
            "source_ref": source_ref,
        }
        item.update(dict(_jsonish(row.get("observed_values_json"), default={})))
        if row.get("comparison_target"):
            item["comparison_target"] = row["comparison_target"]
        return item

    @staticmethod
    def _pet02_uncertainty(row: Mapping[str, Any]) -> dict[str, Any]:
        item = {
            "id": row["id"],
            "assesses": row["assesses"],
            "uncertainty_type": row["uncertainty_type"],
            "representation": row["representation"],
            "material_drivers": list(_jsonish(row.get("material_drivers_json"), default=[])),
        }
        item.update(dict(_jsonish(row.get("assessment_json"), default={})))
        return item


def _jsonish(value: Any, default: Any = None) -> Any:
    if value is None:
        return deepcopy(default)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return deepcopy(default)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return deepcopy(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)
