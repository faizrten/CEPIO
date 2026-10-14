from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from cepio.bootstrap import build_projection_engine, build_runtime
from cepio.model import ObjectRef, OntologyObject, OperationalEvent, Relationship
from cepio.projection import CompressorOperatingStateProjector

UTC = timezone.utc


def _compressor() -> OntologyObject:
    return OntologyObject(
        id="K-201",
        type="Compressor",
        name="Recycle Gas Compressor K-201",
        properties={"criticality": "high"},
        interfaces={"MaintainableAsset", "Inspectable", "RiskBearing"},
    )


def test_object_transaction_history_is_immutable_and_queryable():
    runtime = build_runtime()
    first = runtime.upsert_object(_compressor())
    first_tx = runtime.object_history("K-201")[0].transaction_time

    changed = first.model_copy(deep=True)
    changed.properties["criticality"] = "safety-critical"
    second = runtime.upsert_object(changed, expected_version=first.version)

    history = runtime.object_history("K-201")
    assert [snapshot.object.version for snapshot in history] == [1, 2]
    assert history[0].object.properties["criticality"] == "high"
    assert history[1].object.properties["criticality"] == "safety-critical"
    assert runtime.get_object_at("K-201", first_tx).version == 1
    assert runtime.get_object("K-201").version == 2
    assert second.version == 2


def test_object_valid_time_supports_retroactive_domain_truth():
    runtime = build_runtime()
    v1 = _compressor()
    v1.properties.update({"validFrom": "2026-01-01T00:00:00+00:00", "conditionBand": "healthy"})
    first = runtime.upsert_object(v1)

    v2 = first.model_copy(deep=True)
    v2.properties.update({"validFrom": "2026-02-01T00:00:00+00:00", "conditionBand": "degraded"})
    runtime.upsert_object(v2, expected_version=first.version)

    january = runtime.get_object_valid_at("K-201", datetime(2026, 1, 15, tzinfo=UTC))
    february = runtime.get_object_valid_at("K-201", datetime(2026, 2, 15, tzinfo=UTC))
    assert january.properties["conditionBand"] == "healthy"
    assert february.properties["conditionBand"] == "degraded"


def test_relationship_valid_time_and_transaction_time_are_independent():
    runtime = build_runtime()
    runtime.upsert_object(_compressor())
    runtime.upsert_object(OntologyObject(id="WO-1", type="WorkOrder", name="WO-1"))
    rel = runtime.add_relationship(
        Relationship(
            id="rel-1",
            type="hasWorkOrder",
            source=ObjectRef(id="K-201", type="Compressor"),
            target=ObjectRef(id="WO-1", type="WorkOrder"),
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    first_tx = runtime.relationship_history(rel.id)[0].transaction_time

    runtime.object_repository.revise_relationship_validity(  # type: ignore[attr-defined]
        rel.id,
        valid_to=datetime(2026, 2, 1, tzinfo=UTC),
    )

    assert len(runtime.relationships_at("K-201", datetime(2026, 1, 15, tzinfo=UTC))) == 1
    assert runtime.relationships_at("K-201", datetime(2026, 2, 15, tzinfo=UTC)) == []

    historical_view = runtime.relationships_at(
        "K-201",
        datetime(2026, 2, 15, tzinfo=UTC),
        as_of_transaction=first_tx,
    )
    assert len(historical_view) == 1


def test_sqlite_temporal_history_survives_restart(tmp_path: Path):
    db = tmp_path / "cepio-temporal.db"
    runtime = build_runtime(sqlite_path=db)
    first = runtime.upsert_object(_compressor())
    changed = first.model_copy(deep=True)
    changed.properties["criticality"] = "safety-critical"
    runtime.upsert_object(changed, expected_version=first.version)
    runtime.object_repository.close()  # type: ignore[attr-defined]
    runtime.provenance_repository.close()  # type: ignore[attr-defined]

    reloaded = build_runtime(sqlite_path=db)
    history = reloaded.object_history("K-201")
    assert [snapshot.object.version for snapshot in history] == [1, 2]
    assert history[0].object.properties["criticality"] == "high"
    assert history[1].object.properties["criticality"] == "safety-critical"
    reloaded.object_repository.close()  # type: ignore[attr-defined]
    reloaded.provenance_repository.close()  # type: ignore[attr-defined]


def test_event_projection_is_deterministic_and_source_events_are_immutable():
    runtime = build_runtime()
    runtime.upsert_object(_compressor())
    occurred = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)

    # Insert deliberately out of deterministic order. Tie-breaking by event id means
    # `a-trip` is applied before `z-recovery` at the same timestamp.
    runtime.record_event(
        OperationalEvent(
            id="z-recovery",
            type="RecoveryEvent",
            subject=ObjectRef(id="K-201", type="Compressor"),
            occurred_at=occurred,
        )
    )
    runtime.record_event(
        OperationalEvent(
            id="a-trip",
            type="TripEvent",
            subject=ObjectRef(id="K-201", type="Compressor"),
            occurred_at=occurred,
            properties={"reason": "high vibration"},
        )
    )

    engine = build_projection_engine(runtime)
    projector = CompressorOperatingStateProjector()
    first = engine.rebuild("K-201", projector)
    second = engine.rebuild("K-201", projector)

    assert first.state["operatingState"] == "running"
    assert first.state_hash == second.state_hash
    assert first.event_count == second.event_count == 2
    assert runtime.get_object("K-201").properties["operatingState"] == "running"

    returned_events = runtime.events_for("K-201")
    returned_events[0].properties["tampered"] = True
    assert "tampered" not in runtime.events_for("K-201")[0].properties


def test_projection_can_be_deleted_and_rebuilt_from_source_events():
    runtime = build_runtime()
    runtime.upsert_object(_compressor())
    runtime.record_event(
        OperationalEvent(
            id="trip-1",
            type="TripEvent",
            subject=ObjectRef(id="K-201", type="Compressor"),
            occurred_at=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
        )
    )
    runtime.record_event(
        OperationalEvent(
            id="recover-1",
            type="RecoveryEvent",
            subject=ObjectRef(id="K-201", type="Compressor"),
            occurred_at=datetime(2026, 10, 14, 10, 5, tzinfo=UTC),
        )
    )

    engine = build_projection_engine(runtime)
    projector = CompressorOperatingStateProjector()
    before = engine.rebuild("K-201", projector)
    engine.clear_projection("K-201", projector)
    assert "operatingState" not in runtime.get_object("K-201").properties

    rebuilt = engine.rebuild("K-201", projector)
    assert rebuilt.state_hash == before.state_hash
    assert rebuilt.state["operatingState"] == "running"
    assert len(runtime.events_for("K-201")) == 2


def test_sqlite_projection_checkpoint_survives_restart(tmp_path: Path):
    db = tmp_path / "cepio-projection.db"
    runtime = build_runtime(sqlite_path=db)
    runtime.upsert_object(_compressor())
    runtime.record_event(
        OperationalEvent(
            id="trip-1",
            type="TripEvent",
            subject=ObjectRef(id="K-201", type="Compressor"),
            occurred_at=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
        )
    )
    engine = build_projection_engine(runtime, sqlite_path=db)
    projector = CompressorOperatingStateProjector()
    checkpoint = engine.rebuild("K-201", projector)
    engine.checkpoint_repository.close()  # type: ignore[attr-defined]
    runtime.object_repository.close()  # type: ignore[attr-defined]
    runtime.provenance_repository.close()  # type: ignore[attr-defined]

    reloaded_runtime = build_runtime(sqlite_path=db)
    reloaded_engine = build_projection_engine(reloaded_runtime, sqlite_path=db)
    persisted = reloaded_engine.checkpoint_repository.get_checkpoint(projector.name, "K-201")
    assert persisted is not None
    assert persisted.state_hash == checkpoint.state_hash
    assert persisted.state["operatingState"] == "tripped"
    reloaded_engine.checkpoint_repository.close()  # type: ignore[attr-defined]
    reloaded_runtime.object_repository.close()  # type: ignore[attr-defined]
    reloaded_runtime.provenance_repository.close()  # type: ignore[attr-defined]
