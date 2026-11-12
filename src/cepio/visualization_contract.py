"""CEPIO-owned, host-only read-only visualization intent and provenance v0.1.

Flint is a replaceable presentation compiler, not an evidence source or authority.
This module never performs I/O, calls a model, or executes customer actions.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import ActorContext

CONTRACT_VERSION: Literal["cepio.visualization/0.1"] = "cepio.visualization/0.1"
MAX_POINTS = 500


class EvidenceReference(BaseModel):
    """Versioned reference supplied by a host-resolved evidence binding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_system: str = Field(min_length=1, max_length=80)
    record_id: str = Field(min_length=1, max_length=120)
    record_version: str = Field(min_length=1, max_length=80)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class NumericalObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    measured_at: datetime
    value: float = Field(allow_inf_nan=False)
    evidence: EvidenceReference

    @field_validator("measured_at")
    @classmethod
    def timestamp_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measurement timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


class ChartSeries(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=30)
    semantic_type: Literal["Quantity", "Temperature", "Number"] = "Quantity"
    observations: list[NumericalObservation] = Field(min_length=2, max_length=MAX_POINTS)

    @field_validator("observations")
    @classmethod
    def unique_ordered_timestamp(
        cls, values: list[NumericalObservation]
    ) -> list[NumericalObservation]:
        stamps = [row.measured_at for row in values]
        if stamps != sorted(set(stamps)):
            raise ValueError("observation timestamps must be unique and ascending")
        return values


class VisualizationEnvelope(BaseModel):
    """Portable chart plus evidence ledger; not an upstream authenticity claim."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["cepio.visualization/0.1"] = CONTRACT_VERSION
    qualification: Literal["SYNTHETIC_DEVELOPMENT_ONLY"] = "SYNTHETIC_DEVELOPMENT_ONLY"
    case_id: str
    signal_id: str
    unit: str
    tenant_id: str
    actor_id: str
    data_sha256: str
    provenance_sha256: str
    evidence: list[EvidenceReference]
    flint_input: dict
    fallback_vegalite: dict
    renderer_preference: Literal["flint", "fallback"] = "flint"
    notes: list[str]


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_readonly_visualization(
    *,
    case_id: str,
    tenant_id: str,
    series: ChartSeries,
    principal: Callable[[], ActorContext],
    authorize: Callable[[ActorContext, str, EvidenceReference], bool],
) -> VisualizationEnvelope:
    """Build a chart from host-resolved evidence after per-record authorization.

    Host owns principal, scope and authorization; never populate these from
    untrusted client-side requests. Source attestation belongs to host evidence
    resolution; a supplied SHA digest alone does not prove source authenticity.
    """
    if not case_id or not tenant_id:
        raise ValueError("host must bind a case and tenant")
    # Guard against unvalidated model_copy(update=...) calls by host code.
    series = ChartSeries.model_validate(series.model_dump())
    actor = principal()
    if actor.tenant_id != tenant_id or not actor.actor_id:
        raise PermissionError("principal is not in this tenant")
    for row in series.observations:
        if not authorize(actor, case_id, row.evidence):
            raise PermissionError("evidence read is not authorized")

    rows = [
        {
            "observed_at": row.measured_at.isoformat().replace("+00:00", "Z"),
            "value": row.value,
        }
        for row in series.observations
    ]
    distinct = {ref.model_dump_json(): ref for ref in (row.evidence for row in series.observations)}
    evidence = sorted(
        distinct.values(), key=lambda ref: (ref.source_system, ref.record_id, ref.record_version)
    )
    evidence_ledger = [ref.model_dump(mode="json") for ref in evidence]
    # Flint receives only the authorized rows and their semantic chart intent.
    flint = {
        "data": {"values": rows},
        "semantic_types": {"observed_at": "DateTime", "value": series.semantic_type},
        "chart_spec": {
            "chartType": "Line Chart",
            "encodings": {"x": {"field": "observed_at"}, "y": {"field": "value"}},
            "title": series.title,
            "baseSize": {"width": 520, "height": 300},
        },
        "interaction_spec": {"interactions": [{"type": "inspect-index"}, {"type": "brush-x"}]},
    }
    # Renderer-independent fallback: no third-party code required to export it.
    fallback = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": rows},
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {"field": "observed_at", "type": "temporal", "title": "Time (UTC)"},
            "y": {"field": "value", "type": "quantitative", "title": series.unit},
        },
        "title": series.title,
    }
    return VisualizationEnvelope(
        case_id=case_id,
        signal_id=series.signal_id,
        unit=series.unit,
        tenant_id=tenant_id,
        actor_id=actor.actor_id,
        data_sha256=_digest(rows),
        provenance_sha256=_digest(evidence_ledger),
        evidence=evidence,
        flint_input=flint,
        fallback_vegalite=fallback,
        notes=[
            "Observation chart only: correlation cannot establish a root cause or intervention.",
            "Input rows require host authorization; Flint cannot attest source authenticity.",
            "Synthetic-only development fixture; no live historian, PI or SAP evidence.",
        ],
    )
