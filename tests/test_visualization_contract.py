"""Adversarial, deterministic tests of CEPIO's isolated Flint visualization contract."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from cepio.auth import ActorContext
from cepio.visualization_contract import (
    CONTRACT_VERSION,
    ChartSeries,
    EvidenceReference,
    NumericalObservation,
    build_readonly_visualization,
)


def make_series() -> ChartSeries:
    readings = []
    for day, value in [(1, 2.3), (2, 2.6), (3, 3.1)]:
        readings.append(
            NumericalObservation(
                measured_at=datetime(2026, 11, day, tzinfo=timezone.utc),
                value=value,
                evidence=EvidenceReference(
                    source_system="offline",
                    record_id=f"row-{day}",
                    record_version="1",
                    evidence_sha256=hashlib.sha256(str(value).encode()).hexdigest(),
                ),
            )
        )
    return ChartSeries(
        signal_id="compressor.vibration",
        title="Synthetic vibration",
        unit="mm/s",
        semantic_type="Quantity",
        observations=readings,
    )


def render(*, series=None, principal=None, authorize=None):
    return build_readonly_visualization(
        case_id="K-201",
        tenant_id="synthetic",
        series=series or make_series(),
        principal=principal or (lambda: ActorContext("engineer", {"engineer"}, "synthetic")),
        authorize=authorize or (lambda _actor, _case, _evidence: True),
    )


def test_deterministic_contract_preserves_provenance_without_leakage():
    result = render()
    assert result.contract_version == CONTRACT_VERSION
    assert result.qualification == "SYNTHETIC_DEVELOPMENT_ONLY"
    assert result.data_sha256 == render().data_sha256
    assert result.provenance_sha256 == render().provenance_sha256
    assert result.flint_input["data"]["values"] == render().flint_input["data"]["values"]
    assert len(result.evidence) == 3
    assert result.flint_input["chart_spec"]["chartType"] == "Line Chart"
    assert result.flint_input["interaction_spec"]["interactions"][0]["type"] == "inspect-index"
    assert result.fallback_vegalite["encoding"]["y"]["title"] == "mm/s"
    assert "tenant_id" not in result.flint_input
    assert "actor_id" not in result.flint_input
    assert "evidence" not in result.flint_input
    assert "url" not in result.flint_input["data"]


@pytest.mark.parametrize(
    "actor",
    [
        ActorContext("engineer", set(), "other"),
        ActorContext("engineer", set(), None),
        ActorContext("", set(), "synthetic"),
    ],
)
def test_cross_tenant_or_unnamed_actor_denied_before_authorizing(actor):
    calls = []
    with pytest.raises(PermissionError):
        render(principal=lambda: actor, authorize=lambda *_: calls.append(1) or True)
    assert not calls


def test_revoked_permission_rechecked_every_call():
    allowed = [True]
    render(authorize=lambda *_: allowed[0])
    allowed[0] = False
    with pytest.raises(PermissionError, match="evidence read"):
        render(authorize=lambda *_: allowed[0])


def test_one_denied_record_blocks_entire_chart():
    with pytest.raises(PermissionError):
        render(authorize=lambda _actor, _case, ref: ref.record_id != "row-2")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numbers_are_rejected(value):
    reading = make_series().observations[0].model_dump()
    reading["value"] = value
    with pytest.raises(ValidationError):
        NumericalObservation.model_validate(reading)


def test_duplicate_and_unsorted_timestamps_are_rejected():
    readings = make_series().observations
    record = make_series().model_dump()
    record["observations"] = [readings[0].model_dump(), readings[0].model_dump()]
    with pytest.raises(ValidationError):
        ChartSeries.model_validate(record)
    record["observations"] = [readings[1].model_dump(), readings[0].model_dump()]
    with pytest.raises(ValidationError):
        ChartSeries.model_validate(record)


def test_naive_timestamp_is_rejected():
    record = make_series().observations[0].model_dump()
    record["measured_at"] = "2026-11-01T12:00:00"
    with pytest.raises(ValidationError):
        NumericalObservation.model_validate(record)


def test_invalid_evidence_digest_is_rejected():
    with pytest.raises(ValidationError):
        EvidenceReference(
            source_system="x", record_id="y", record_version="1", evidence_sha256="invalid"
        )


def test_bypassed_model_copy_update_is_revalidated_at_boundary():
    series = make_series()
    forged = series.model_copy(update={"observations": []})
    with pytest.raises(ValidationError):
        render(series=forged)


def test_fixture_produces_three_independent_unit_safe_charts():
    # Importing an offline local example is not an authenticated API entry point.
    from examples.flint_k201_offline import make_examples

    charts = make_examples()
    assert len(charts) == 3
    assert {chart["unit"] for chart in charts} == {"mm/s", "degC", "%"}
    assert all(len(chart["flint_input"]["data"]["values"]) == 8 for chart in charts)
    assert all(len(chart["evidence"]) == 8 for chart in charts)
    assert all(chart["qualification"] == "SYNTHETIC_DEVELOPMENT_ONLY" for chart in charts)
    assert len({chart["data_sha256"] for chart in charts}) == 3
