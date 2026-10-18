from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, OperationalEvent, Relationship
from cepio.query import ObjectQuery, PropertyPredicate, QueryOperator

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_V01 = ROOT / "mvp/datasets/drilling-v0.1"
FIXTURE_V02 = ROOT / "mvp/datasets/drilling-v0.2"
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _load_v02_generator():
    path = ROOT / "scripts/extend_drilling_mvp_multimodal_v02.py"
    spec = importlib.util.spec_from_file_location("extend_drilling_mvp_multimodal_v02", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load v0.2 generator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ref(runtime, object_id: str) -> ObjectRef:
    obj = runtime.get_object(object_id)
    return ObjectRef(id=obj.id, type=obj.type)


<<<<<<< HEAD
def _add_relationship(
    runtime, rel_id: str, rel_type: str, source_id: str, target_id: str, source_uri: str
) -> None:
=======
def _add_relationship(runtime, rel_id: str, rel_type: str, source_id: str, target_id: str, source_uri: str) -> None:
>>>>>>> origin/main
    runtime.add_relationship(
        Relationship(
            id=rel_id,
            type=rel_type,
            source=_ref(runtime, source_id),
            target=_ref(runtime, target_id),
            properties={"source_uri": source_uri, "synthetic": True},
        )
    )


<<<<<<< HEAD
def _upsert(
    runtime, object_id: str, object_type: str, name: str, properties: dict[str, Any]
) -> None:
=======
def _upsert(runtime, object_id: str, object_type: str, name: str, properties: dict[str, Any]) -> None:
>>>>>>> origin/main
    runtime.upsert_object(
        OntologyObject(
            id=object_id,
            type=object_type,
            name=name,
            properties=properties,
        )
    )


def _telemetry_stats(path: Path) -> dict[str, dict[str, Any]]:
    values: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            values[row["sensor_id"]].append((_dt(row["timestamp"]), float(row["value"])))

    result: dict[str, dict[str, Any]] = {}
    for sensor_id, samples in values.items():
        series = np.asarray([value for _, value in samples], dtype=float)
        stats: dict[str, Any] = {
            "sample_count": len(samples),
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
        }
        if sensor_id.startswith("rig-07-mud-pump-01-"):
<<<<<<< HEAD
            pre = [
                value
                for when, value in samples
                if START + timedelta(days=30) <= when <= START + timedelta(days=35)
            ]
            post = [
                value
                for when, value in samples
                if START + timedelta(days=36) <= when <= START + timedelta(days=41)
            ]
=======
            pre = [value for when, value in samples if START + timedelta(days=30) <= when <= START + timedelta(days=35)]
            post = [value for when, value in samples if START + timedelta(days=36) <= when <= START + timedelta(days=41)]
>>>>>>> origin/main
            if pre and post:
                pre_mean = float(np.mean(pre))
                post_mean = float(np.mean(post))
                stats.update(
                    {
                        "pre_failure_mean": pre_mean,
                        "post_repair_mean": post_mean,
                        "repair_normalized": post_mean < pre_mean,
                    }
                )
        result[sensor_id] = stats
    return result


def build_acceptance_runtime(dataset_dir: Path):
    runtime = build_runtime(validate_types=True, validate_properties=False)
    aliases = {
        item["canonical_id"]: item["aliases"]
        for item in _read_json(FIXTURE_V01 / "ground-truth/entity-resolution.json")
    }
    scenarios = _read_json(FIXTURE_V01 / "ground-truth/scenarios.json")
    scenario_by_equipment = {item["equipment_id"]: item for item in scenarios}

    for row in _read_csv(dataset_dir / "master-data/rigs.csv"):
        _upsert(
            runtime,
            row["rig_id"],
            "OperatingRig",
            row["name"],
            {
                "canonical_iri": row["canonical_iri"],
                "rig_type": row["rig_type"],
                "status": row["status"],
                "source_uri": "master-data/rigs.csv",
            },
        )

    for row in _read_csv(dataset_dir / "operations/wells.csv"):
        _upsert(
            runtime,
            row["well_id"],
            "Well",
            row["name"],
            {
                "canonical_iri": row["canonical_iri"],
                "rig_id": row["rig_id"],
                "status": row["status"],
                "source_uri": "operations/wells.csv",
            },
        )
<<<<<<< HEAD
        _add_relationship(
            runtime,
            f"REL-{row['rig_id']}-{row['well_id']}",
            "workingOnWell",
            row["rig_id"],
            row["well_id"],
            "operations/wells.csv",
        )
=======
        _add_relationship(runtime, f"REL-{row['rig_id']}-{row['well_id']}", "workingOnWell", row["rig_id"], row["well_id"], "operations/wells.csv")
>>>>>>> origin/main

    for row in _read_csv(dataset_dir / "master-data/equipment.csv"):
        scenario = scenario_by_equipment.get(row["equipment_id"])
        properties: dict[str, Any] = {
            "canonical_iri": row["canonical_iri"],
            "rig_id": row["rig_id"],
            "equipment_type": row["equipment_type"],
            "manufacturer": row["manufacturer"],
            "model": row["model"],
            "criticality": row["criticality"],
            "aliases": aliases.get(row["equipment_id"], {}),
            "source_uri": "master-data/equipment.csv",
        }
        if scenario:
            properties.update(
                {
                    "scenario_id": scenario["scenario_id"],
                    "root_cause": scenario["root_cause"],
                    "leading_signals": scenario["leading_signals"],
                }
            )
        _upsert(runtime, row["equipment_id"], "DrillingEquipment", row["name"], properties)
<<<<<<< HEAD
        _add_relationship(
            runtime,
            f"REL-{row['rig_id']}-{row['equipment_id']}",
            "hasRigEquipment",
            row["rig_id"],
            row["equipment_id"],
            "master-data/equipment.csv",
        )
=======
        _add_relationship(runtime, f"REL-{row['rig_id']}-{row['equipment_id']}", "hasRigEquipment", row["rig_id"], row["equipment_id"], "master-data/equipment.csv")
>>>>>>> origin/main

    telemetry_stats = _telemetry_stats(dataset_dir / "telemetry/telemetry.csv")
    for row in _read_csv(dataset_dir / "master-data/sensors.csv"):
        properties = {
            "canonical_iri": row["canonical_iri"],
            "equipment_id": row["equipment_id"],
            "metric": row["signal_type"],
            "unit": row["unit"],
            "source_tag": row["source_tag"],
            "source_uri": "telemetry/telemetry.csv",
            **telemetry_stats.get(row["sensor_id"], {}),
        }
<<<<<<< HEAD
        _upsert(
            runtime,
            row["sensor_id"],
            "ConditionSignal",
            row["signal_type"].replace("_", " ").title(),
            properties,
        )
        _add_relationship(
            runtime,
            f"REL-{row['sensor_id']}-observes",
            "observedOnEquipment",
            row["sensor_id"],
            row["equipment_id"],
            "master-data/sensors.csv",
        )
=======
        _upsert(runtime, row["sensor_id"], "ConditionSignal", row["signal_type"].replace("_", " ").title(), properties)
        _add_relationship(runtime, f"REL-{row['sensor_id']}-observes", "observedOnEquipment", row["sensor_id"], row["equipment_id"], "master-data/sensors.csv")
>>>>>>> origin/main

    work_by_scenario: dict[str, str] = {}
    for row in _read_csv(dataset_dir / "maintenance/work_orders.csv"):
        work_by_scenario[row["scenario_id"]] = row["work_order_id"]
        _upsert(
            runtime,
            row["work_order_id"],
            "WorkOrder",
            row["description"],
            {
                "equipment_id": row["equipment_id"],
                "status": row["status"],
                "priority": row["priority"],
                "created_time": row["created_time"],
                "completed_time": row["completed_time"],
                "scenario_id": row["scenario_id"],
                "source_uri": "maintenance/work_orders.csv",
            },
        )
<<<<<<< HEAD
        _add_relationship(
            runtime,
            f"REL-{row['equipment_id']}-{row['work_order_id']}",
            "hasWorkOrder",
            row["equipment_id"],
            row["work_order_id"],
            "maintenance/work_orders.csv",
        )
=======
        _add_relationship(runtime, f"REL-{row['equipment_id']}-{row['work_order_id']}", "hasWorkOrder", row["equipment_id"], row["work_order_id"], "maintenance/work_orders.csv")
>>>>>>> origin/main

    downtime_by_scenario: dict[str, str] = {}
    for row in _read_csv(dataset_dir / "operations/npt_events.csv"):
        downtime_by_scenario[row["scenario_id"]] = row["npt_event_id"]
        _upsert(
            runtime,
            row["npt_event_id"],
            "DowntimeEvent",
            row["category"].replace("_", " ").title(),
            {
                "rig_id": row["rig_id"],
                "well_id": row["well_id"],
                "equipment_id": row["equipment_id"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "duration_hours": float(row["duration_hours"]),
                "category": row["category"],
                "scenario_id": row["scenario_id"],
                "source_uri": "operations/npt_events.csv",
            },
        )
<<<<<<< HEAD
        _add_relationship(
            runtime,
            f"REL-{row['npt_event_id']}-{row['equipment_id']}",
            "dependsOn",
            row["npt_event_id"],
            row["equipment_id"],
            "operations/npt_events.csv",
        )
=======
        _add_relationship(runtime, f"REL-{row['npt_event_id']}-{row['equipment_id']}", "dependsOn", row["npt_event_id"], row["equipment_id"], "operations/npt_events.csv")
>>>>>>> origin/main
        runtime.record_event(
            OperationalEvent(
                id=f"EV-{row['npt_event_id']}",
                type="RigOperationalEvent",
                subject=_ref(runtime, row["equipment_id"]),
                occurred_at=_dt(row["start_time"]),
                severity="high",
<<<<<<< HEAD
                properties={
                    "npt_event_id": row["npt_event_id"],
                    "duration_hours": float(row["duration_hours"]),
                    "scenario_id": row["scenario_id"],
                },
=======
                properties={"npt_event_id": row["npt_event_id"], "duration_hours": float(row["duration_hours"]), "scenario_id": row["scenario_id"]},
>>>>>>> origin/main
                source_system="synthetic_npt",
            )
        )

    for row in _read_csv(dataset_dir / "reliability/failure_events.csv"):
        _upsert(
            runtime,
            row["failure_event_id"],
            "FailureEvent",
            row["failure_mode"].replace("-", " ").title(),
            {
                "equipment_id": row["equipment_id"],
                "timestamp": row["timestamp"],
                "failure_mode": row["failure_mode"],
                "scenario_id": row["scenario_id"],
                "source_uri": "reliability/failure_events.csv",
            },
        )
<<<<<<< HEAD
        _add_relationship(
            runtime,
            f"REL-{row['failure_event_id']}-equipment",
            "failureOfEquipment",
            row["failure_event_id"],
            row["equipment_id"],
            "reliability/failure_events.csv",
        )
        work_order = work_by_scenario.get(row["scenario_id"])
        if work_order:
            _add_relationship(
                runtime,
                f"REL-{row['failure_event_id']}-work",
                "repairedByWorkOrder",
                row["failure_event_id"],
                work_order,
                "maintenance/work_orders.csv",
            )
        downtime = downtime_by_scenario.get(row["scenario_id"])
        if downtime:
            _add_relationship(
                runtime,
                f"REL-{row['failure_event_id']}-downtime",
                "causesDowntime",
                row["failure_event_id"],
                downtime,
                "operations/npt_events.csv",
            )
=======
        _add_relationship(runtime, f"REL-{row['failure_event_id']}-equipment", "failureOfEquipment", row["failure_event_id"], row["equipment_id"], "reliability/failure_events.csv")
        work_order = work_by_scenario.get(row["scenario_id"])
        if work_order:
            _add_relationship(runtime, f"REL-{row['failure_event_id']}-work", "repairedByWorkOrder", row["failure_event_id"], work_order, "maintenance/work_orders.csv")
        downtime = downtime_by_scenario.get(row["scenario_id"])
        if downtime:
            _add_relationship(runtime, f"REL-{row['failure_event_id']}-downtime", "causesDowntime", row["failure_event_id"], downtime, "operations/npt_events.csv")
>>>>>>> origin/main
        runtime.record_event(
            OperationalEvent(
                id=f"EV-{row['failure_event_id']}",
                type="FailureEvent",
                subject=_ref(runtime, row["equipment_id"]),
                occurred_at=_dt(row["timestamp"]),
                severity="high",
<<<<<<< HEAD
                properties={
                    "failure_event_id": row["failure_event_id"],
                    "failure_mode": row["failure_mode"],
                    "scenario_id": row["scenario_id"],
                },
=======
                properties={"failure_event_id": row["failure_event_id"], "failure_mode": row["failure_mode"], "scenario_id": row["scenario_id"]},
>>>>>>> origin/main
                source_system="synthetic_reliability",
            )
        )

    for row in _read_csv(dataset_dir / "operations/activities.csv"):
        _upsert(
            runtime,
            row["activity_id"],
            "ActivityInterval",
            f"{row['classification']} {row['activity_id']}",
            {
                "rig_id": row["rig_id"],
                "well_id": row["well_id"],
                "classification": row["classification"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "source_uri": "operations/activities.csv",
            },
        )
<<<<<<< HEAD
        _add_relationship(
            runtime,
            f"REL-{row['activity_id']}-rig",
            "activityOnRig",
            row["activity_id"],
            row["rig_id"],
            "operations/activities.csv",
        )
        _add_relationship(
            runtime,
            f"REL-{row['activity_id']}-well",
            "activityForWell",
            row["activity_id"],
            row["well_id"],
            "operations/activities.csv",
        )
=======
        _add_relationship(runtime, f"REL-{row['activity_id']}-rig", "activityOnRig", row["activity_id"], row["rig_id"], "operations/activities.csv")
        _add_relationship(runtime, f"REL-{row['activity_id']}-well", "activityForWell", row["activity_id"], row["well_id"], "operations/activities.csv")
>>>>>>> origin/main

    generator = _load_v02_generator()
    scenario_specs = generator.SCENARIOS
    artifact_index = _read_json(dataset_dir / "multimodal/artifact-index.json")
    for artifact in artifact_index["artifacts"]:
        if artifact["modality"] == "document" and "daily-drilling-reports" in artifact["path"]:
            object_type = "DailyDrillingReport"
        elif artifact["modality"] == "document":
            object_type = "Document"
        else:
            object_type = "DigitalAsset"
        spec = scenario_specs.get(artifact["scenario_id"], {})
        properties = {
            "modality": artifact["modality"],
            "mime_type": artifact["mime_type"],
            "source_uri": artifact["path"],
            "source_asset_iri": artifact["canonical_iri"],
            "equipment_id": artifact["equipment_id"],
            "scenario_id": artifact["scenario_id"],
            "event_time": artifact["event_time"],
            "ground_truth_claims": artifact["ground_truth_claims"],
            "provenance": artifact["provenance"],
            "raw_payload_embedded": False,
        }
        if artifact["modality"] == "high_frequency_signal":
            properties.update(
                {
                    "sample_rate_hz": 2048.0,
                    "base_frequency_hz": float(spec["base_frequency_hz"]),
                    "fault_frequency_hz": float(spec["fault_frequency_hz"]),
                }
            )
<<<<<<< HEAD
        _upsert(
            runtime, artifact["artifact_id"], object_type, Path(artifact["path"]).name, properties
        )
        _add_relationship(
            runtime,
            f"REL-{artifact['artifact_id']}-asset",
            "dependsOn",
            artifact["artifact_id"],
            artifact["equipment_id"],
            artifact["path"],
        )
=======
        _upsert(runtime, artifact["artifact_id"], object_type, Path(artifact["path"]).name, properties)
        _add_relationship(runtime, f"REL-{artifact['artifact_id']}-asset", "dependsOn", artifact["artifact_id"], artifact["equipment_id"], artifact["path"])
>>>>>>> origin/main

    geo = _read_json(dataset_dir / "geospatial/rig-well-context.geojson")
    for feature in geo["features"]:
        if feature["geometry"]["type"] != "Point":
            continue
        object_id = feature["id"]
        try:
            obj = runtime.get_object(object_id)
        except KeyError:
            continue
        longitude, latitude = feature["geometry"]["coordinates"]
        properties = dict(obj.properties)
        properties.update(
            {
                "longitude": float(longitude),
                "latitude": float(latitude),
                "geospatial_source_uri": "geospatial/rig-well-context.geojson",
            }
        )
<<<<<<< HEAD
        runtime.upsert_object(
            obj.model_copy(update={"properties": properties}), expected_version=obj.version
        )
=======
        runtime.upsert_object(obj.model_copy(update={"properties": properties}), expected_version=obj.version)
>>>>>>> origin/main

    return runtime


<<<<<<< HEAD
def _query(
    runtime, object_type: str, property_name: str | None = None, value: Any | None = None
) -> list[OntologyObject]:
    predicates = []
    if property_name is not None:
        predicates.append(
            PropertyPredicate(property=property_name, operator=QueryOperator.eq, value=value)
        )
    return runtime.query_objects(
        ObjectQuery(object_type=object_type, predicates=predicates, limit=200)
    ).items


def _artifact_objects(
    runtime, scenario_id: str | None = None, modality: str | None = None
) -> list[OntologyObject]:
    result = [
        obj
        for obj in runtime.list_objects()
        if obj.type in {"Document", "DailyDrillingReport", "DigitalAsset"}
        and "modality" in obj.properties
    ]
=======
def _query(runtime, object_type: str, property_name: str | None = None, value: Any | None = None) -> list[OntologyObject]:
    predicates = []
    if property_name is not None:
        predicates.append(PropertyPredicate(property=property_name, operator=QueryOperator.eq, value=value))
    return runtime.query_objects(ObjectQuery(object_type=object_type, predicates=predicates, limit=200)).items


def _artifact_objects(runtime, scenario_id: str | None = None, modality: str | None = None) -> list[OntologyObject]:
    result = [obj for obj in runtime.list_objects() if obj.type in {"Document", "DailyDrillingReport", "DigitalAsset"} and "modality" in obj.properties]
>>>>>>> origin/main
    if scenario_id is not None:
        result = [obj for obj in result if obj.properties.get("scenario_id") == scenario_id]
    if modality is not None:
        result = [obj for obj in result if obj.properties.get("modality") == modality]
    return result


def _waveform_has_fault_component(dataset_dir: Path, artifact: OntologyObject) -> bool:
    path = dataset_dir / str(artifact.properties["source_uri"])
    rows = _read_csv(path)
    values = np.asarray([float(row["value"]) for row in rows], dtype=float)
    values = values - values.mean()
    spectrum = np.abs(np.fft.rfft(values))
    frequencies = np.fft.rfftfreq(len(values), d=1.0 / float(artifact.properties["sample_rate_hz"]))

    def amplitude(target: float) -> float:
        index = int(np.argmin(np.abs(frequencies - target)))
        return float(spectrum[index])

    base_amp = amplitude(float(artifact.properties["base_frequency_hz"]))
    fault_amp = amplitude(float(artifact.properties["fault_frequency_hz"]))
    noise_floor = float(np.median(spectrum[1:])) if len(spectrum) > 1 else 0.0
    return base_amp > noise_floor * 3.0 and fault_amp > noise_floor * 3.0


def answer_golden_question(runtime, dataset_dir: Path, question_id: str) -> dict[str, Any]:
    if question_id == "GQ-001":
<<<<<<< HEAD
        return {
            "refs": [obj.id for obj in runtime.neighbors("rig-07", "hasRigEquipment")],
            "evidence": ["master-data/equipment.csv"],
        }
    if question_id == "GQ-002":
        return {
            "refs": [
                obj.id
                for obj in runtime.reverse_neighbors("rig-07-mud-pump-01", "observedOnEquipment")
            ],
            "evidence": ["master-data/sensors.csv", "telemetry/telemetry.csv"],
        }
    if question_id == "GQ-003":
        aliases = runtime.get_object("rig-07-mud-pump-01").properties["aliases"]
        return {
            "refs": list(aliases.values()),
            "evidence": ["mvp/datasets/drilling-v0.1/ground-truth/entity-resolution.json"],
        }
=======
        return {"refs": [obj.id for obj in runtime.neighbors("rig-07", "hasRigEquipment")], "evidence": ["master-data/equipment.csv"]}
    if question_id == "GQ-002":
        return {"refs": [obj.id for obj in runtime.reverse_neighbors("rig-07-mud-pump-01", "observedOnEquipment")], "evidence": ["master-data/sensors.csv", "telemetry/telemetry.csv"]}
    if question_id == "GQ-003":
        aliases = runtime.get_object("rig-07-mud-pump-01").properties["aliases"]
        return {"refs": list(aliases.values()), "evidence": ["mvp/datasets/drilling-v0.1/ground-truth/entity-resolution.json"]}
>>>>>>> origin/main
    if question_id == "GQ-004":
        equipment = runtime.get_object("rig-07-mud-pump-01")
        failures = runtime.reverse_neighbors(equipment.id, "failureOfEquipment")
        refs = list(equipment.properties.get("leading_signals", [])) + [obj.id for obj in failures]
<<<<<<< HEAD
        return {
            "refs": refs,
            "evidence": ["telemetry/telemetry.csv", "reliability/failure_events.csv"],
        }
    if question_id == "GQ-005":
        downtime = runtime.traverse("FAIL-001", ["causesDowntime"])[0]
        return {
            "value": downtime.properties["duration_hours"],
            "evidence": [downtime.properties["source_uri"]],
        }
=======
        return {"refs": refs, "evidence": ["telemetry/telemetry.csv", "reliability/failure_events.csv"]}
    if question_id == "GQ-005":
        downtime = runtime.traverse("FAIL-001", ["causesDowntime"])[0]
        return {"value": downtime.properties["duration_hours"], "evidence": [downtime.properties["source_uri"]]}
>>>>>>> origin/main
    if question_id == "GQ-006":
        work = runtime.traverse("FAIL-001", ["repairedByWorkOrder"])
        return {"refs": [obj.id for obj in work], "evidence": ["maintenance/work_orders.csv"]}
    if question_id == "GQ-007":
        signals = runtime.reverse_neighbors("rig-07-mud-pump-01", "observedOnEquipment")
<<<<<<< HEAD
        target = [
            obj
            for obj in signals
            if obj.properties.get("metric") in {"vibration_rms", "bearing_temperature"}
        ]
        return {
            "value": bool(target)
            and all(bool(obj.properties.get("repair_normalized")) for obj in target),
            "evidence": ["telemetry/telemetry.csv"],
        }
=======
        target = [obj for obj in signals if obj.properties.get("metric") in {"vibration_rms", "bearing_temperature"}]
        return {"value": bool(target) and all(bool(obj.properties.get("repair_normalized")) for obj in target), "evidence": ["telemetry/telemetry.csv"]}
>>>>>>> origin/main
    if question_id == "GQ-008":
        equipment = runtime.get_object("rig-12-top-drive-01")
        work = runtime.neighbors(equipment.id, "hasWorkOrder")
        failures = runtime.reverse_neighbors(equipment.id, "failureOfEquipment")
        if any(obj.properties.get("status") == "open" for obj in work) and not failures:
<<<<<<< HEAD
            return {
                "refs": [equipment.properties["rig_id"], equipment.id],
                "evidence": ["maintenance/work_orders.csv", "reliability/failure_events.csv"],
            }
        return {
            "refs": [],
            "evidence": ["maintenance/work_orders.csv", "reliability/failure_events.csv"],
        }
    if question_id == "GQ-009":
        work = [
            obj
            for obj in runtime.neighbors("rig-12-top-drive-01", "hasWorkOrder")
            if obj.properties.get("status") == "open"
        ]
        return {"refs": [obj.id for obj in work], "evidence": ["maintenance/work_orders.csv"]}
    if question_id == "GQ-010":
        npt = [
            obj
            for obj in _query(runtime, "DowntimeEvent")
            if obj.properties.get("category") == "well_control_test_failure"
        ]
=======
            return {"refs": [equipment.properties["rig_id"], equipment.id], "evidence": ["maintenance/work_orders.csv", "reliability/failure_events.csv"]}
        return {"refs": [], "evidence": ["maintenance/work_orders.csv", "reliability/failure_events.csv"]}
    if question_id == "GQ-009":
        work = [obj for obj in runtime.neighbors("rig-12-top-drive-01", "hasWorkOrder") if obj.properties.get("status") == "open"]
        return {"refs": [obj.id for obj in work], "evidence": ["maintenance/work_orders.csv"]}
    if question_id == "GQ-010":
        npt = [obj for obj in _query(runtime, "DowntimeEvent") if obj.properties.get("category") == "well_control_test_failure"]
>>>>>>> origin/main
        refs = []
        for obj in npt:
            refs.extend([obj.properties["scenario_id"], obj.id])
        return {"refs": refs, "evidence": ["operations/npt_events.csv"]}
    if question_id == "GQ-011":
        obj = runtime.get_object("NPT-003")
<<<<<<< HEAD
        return {
            "value": obj.properties["duration_hours"],
            "evidence": [obj.properties["source_uri"]],
        }
    if question_id == "GQ-012":
        matches = _query(runtime, "DrillingEquipment", "scenario_id", "SCN-004")
        return {
            "refs": [obj.id for obj in matches],
            "evidence": ["telemetry/telemetry.csv", "master-data/equipment.csv"],
        }
    if question_id == "GQ-013":
        obj = runtime.get_object("rig-12-mud-pump-02")
        return {
            "refs": [obj.properties["root_cause"]],
            "evidence": [
                "mvp/datasets/drilling-v0.1/ground-truth/scenarios.json",
                "reliability/failure_events.csv",
            ],
        }
=======
        return {"value": obj.properties["duration_hours"], "evidence": [obj.properties["source_uri"]]}
    if question_id == "GQ-012":
        matches = _query(runtime, "DrillingEquipment", "scenario_id", "SCN-004")
        return {"refs": [obj.id for obj in matches], "evidence": ["telemetry/telemetry.csv", "master-data/equipment.csv"]}
    if question_id == "GQ-013":
        obj = runtime.get_object("rig-12-mud-pump-02")
        return {"refs": [obj.properties["root_cause"]], "evidence": ["mvp/datasets/drilling-v0.1/ground-truth/scenarios.json", "reliability/failure_events.csv"]}
>>>>>>> origin/main
    if question_id == "GQ-014":
        refs = sorted({obj.properties["scenario_id"] for obj in _query(runtime, "DowntimeEvent")})
        return {"refs": refs, "evidence": ["operations/npt_events.csv"]}
    if question_id == "GQ-015":
<<<<<<< HEAD
        obj = max(
            _query(runtime, "DowntimeEvent"),
            key=lambda item: float(item.properties["duration_hours"]),
        )
        return {"refs": [obj.id], "evidence": [obj.properties["source_uri"]]}
    if question_id == "GQ-016":
        pumps = _query(runtime, "DrillingEquipment", "equipment_type", "MudPump")
        return {
            "refs": sorted({obj.properties["rig_id"] for obj in pumps}),
            "evidence": ["master-data/equipment.csv"],
        }
    if question_id == "GQ-017":
        equipment = runtime.get_object("rig-12-top-drive-01")
        open_work = any(
            obj.properties.get("status") == "open"
            for obj in runtime.neighbors(equipment.id, "hasWorkOrder")
        )
        realized = any(
            obj.properties.get("scenario_id") == "SCN-002"
            for obj in _query(runtime, "DowntimeEvent")
        )
        return {
            "refs": ["SCN-002"] if open_work and not realized else [],
            "evidence": ["maintenance/work_orders.csv", "operations/npt_events.csv"],
        }
    if question_id == "GQ-018":
        work = _query(runtime, "WorkOrder")
        ok = all(
            runtime.reverse_neighbors(obj.id, "hasWorkOrder") and obj.properties.get("scenario_id")
            for obj in work
        )
        return {
            "value": bool(ok),
            "evidence": ["maintenance/work_orders.csv", "master-data/equipment.csv"],
        }
=======
        obj = max(_query(runtime, "DowntimeEvent"), key=lambda item: float(item.properties["duration_hours"]))
        return {"refs": [obj.id], "evidence": [obj.properties["source_uri"]]}
    if question_id == "GQ-016":
        pumps = _query(runtime, "DrillingEquipment", "equipment_type", "MudPump")
        return {"refs": sorted({obj.properties["rig_id"] for obj in pumps}), "evidence": ["master-data/equipment.csv"]}
    if question_id == "GQ-017":
        equipment = runtime.get_object("rig-12-top-drive-01")
        open_work = any(obj.properties.get("status") == "open" for obj in runtime.neighbors(equipment.id, "hasWorkOrder"))
        realized = any(obj.properties.get("scenario_id") == "SCN-002" for obj in _query(runtime, "DowntimeEvent"))
        return {"refs": ["SCN-002"] if open_work and not realized else [], "evidence": ["maintenance/work_orders.csv", "operations/npt_events.csv"]}
    if question_id == "GQ-018":
        work = _query(runtime, "WorkOrder")
        ok = all(runtime.reverse_neighbors(obj.id, "hasWorkOrder") and obj.properties.get("scenario_id") for obj in work)
        return {"value": bool(ok), "evidence": ["maintenance/work_orders.csv", "master-data/equipment.csv"]}
>>>>>>> origin/main
    if question_id == "GQ-019":
        refs = []
        for obj in _query(runtime, "DrillingEquipment"):
            if "MP-001" in obj.properties.get("aliases", {}).values():
                refs.append(obj.properties["canonical_iri"])
<<<<<<< HEAD
        return {
            "refs": refs,
            "evidence": ["mvp/datasets/drilling-v0.1/ground-truth/entity-resolution.json"],
        }
    if question_id == "GQ-020":
        obj = max(
            _query(runtime, "DowntimeEvent"),
            key=lambda item: float(item.properties["duration_hours"]),
        )
        return {"refs": [obj.properties["scenario_id"]], "evidence": [obj.properties["source_uri"]]}
    if question_id == "GQ-021":
        docs = [
            obj
            for obj in _artifact_objects(runtime, "SCN-001", "document")
            if "inspection-reports" in obj.properties["source_uri"]
        ]
        refs: list[str] = []
        for obj in docs:
            refs.extend(
                [
                    obj.properties["scenario_id"],
                    *obj.properties["ground_truth_claims"],
                    obj.properties["source_asset_iri"],
                ]
            )
        return {"refs": refs, "evidence": [obj.properties["source_uri"] for obj in docs]}
    if question_id == "GQ-022":
        images = _artifact_objects(runtime, "SCN-001", "inspection_image")
        refs = ["SCN-001"] + [
            claim for obj in images for claim in obj.properties["ground_truth_claims"]
        ]
        return {"refs": refs, "evidence": [obj.properties["source_uri"] for obj in images]}
    if question_id == "GQ-023":
        diagrams = _artifact_objects(runtime, "SCN-003", "engineering_diagram")
        refs = ["SCN-003"] + [
            claim for obj in diagrams for claim in obj.properties["ground_truth_claims"]
        ]
        return {"refs": refs, "evidence": [obj.properties["source_uri"] for obj in diagrams]}
    if question_id == "GQ-024":
        rigs = [
            obj
            for obj in _query(runtime, "OperatingRig")
            if "longitude" in obj.properties and "latitude" in obj.properties
        ]
        return {
            "refs": [obj.id for obj in rigs],
            "evidence": ["geospatial/rig-well-context.geojson"],
        }
    if question_id == "GQ-025":
        wells = [
            obj
            for obj in _query(runtime, "Well", "rig_id", "rig-12")
            if "longitude" in obj.properties
        ]
        return {
            "refs": [obj.id for obj in wells],
            "evidence": ["geospatial/rig-well-context.geojson"],
        }
    if question_id == "GQ-026":
        waveform = _artifact_objects(runtime, "SCN-001", "high_frequency_signal")[0]
        return {
            "value": _waveform_has_fault_component(dataset_dir, waveform),
            "evidence": [waveform.properties["source_uri"]],
        }
    if question_id == "GQ-027":
        modalities = sorted(
            {obj.properties["modality"] for obj in _artifact_objects(runtime, "SCN-004")}
        )
        return {
            "refs": modalities,
            "evidence": [
                obj.properties["source_uri"] for obj in _artifact_objects(runtime, "SCN-004")
            ],
        }
    if question_id == "GQ-028":
        artifacts = _artifact_objects(runtime)
        ok = all(
            obj.properties.get("source_uri") and obj.properties.get("raw_payload_embedded") is False
            for obj in artifacts
        )
        return {"value": bool(ok), "evidence": ["multimodal/artifact-index.json"]}
    if question_id == "GQ-029":
        artifacts = _artifact_objects(runtime)
        ok = all(
            obj.properties.get("source_asset_iri")
            and obj.properties.get("scenario_id")
            and obj.properties.get("event_time")
            and obj.properties.get("provenance")
            for obj in artifacts
        )
=======
        return {"refs": refs, "evidence": ["mvp/datasets/drilling-v0.1/ground-truth/entity-resolution.json"]}
    if question_id == "GQ-020":
        obj = max(_query(runtime, "DowntimeEvent"), key=lambda item: float(item.properties["duration_hours"]))
        return {"refs": [obj.properties["scenario_id"]], "evidence": [obj.properties["source_uri"]]}
    if question_id == "GQ-021":
        docs = [obj for obj in _artifact_objects(runtime, "SCN-001", "document") if "inspection-reports" in obj.properties["source_uri"]]
        refs: list[str] = []
        for obj in docs:
            refs.extend([obj.properties["scenario_id"], *obj.properties["ground_truth_claims"], obj.properties["source_asset_iri"]])
        return {"refs": refs, "evidence": [obj.properties["source_uri"] for obj in docs]}
    if question_id == "GQ-022":
        images = _artifact_objects(runtime, "SCN-001", "inspection_image")
        refs = ["SCN-001"] + [claim for obj in images for claim in obj.properties["ground_truth_claims"]]
        return {"refs": refs, "evidence": [obj.properties["source_uri"] for obj in images]}
    if question_id == "GQ-023":
        diagrams = _artifact_objects(runtime, "SCN-003", "engineering_diagram")
        refs = ["SCN-003"] + [claim for obj in diagrams for claim in obj.properties["ground_truth_claims"]]
        return {"refs": refs, "evidence": [obj.properties["source_uri"] for obj in diagrams]}
    if question_id == "GQ-024":
        rigs = [obj for obj in _query(runtime, "OperatingRig") if "longitude" in obj.properties and "latitude" in obj.properties]
        return {"refs": [obj.id for obj in rigs], "evidence": ["geospatial/rig-well-context.geojson"]}
    if question_id == "GQ-025":
        wells = [obj for obj in _query(runtime, "Well", "rig_id", "rig-12") if "longitude" in obj.properties]
        return {"refs": [obj.id for obj in wells], "evidence": ["geospatial/rig-well-context.geojson"]}
    if question_id == "GQ-026":
        waveform = _artifact_objects(runtime, "SCN-001", "high_frequency_signal")[0]
        return {"value": _waveform_has_fault_component(dataset_dir, waveform), "evidence": [waveform.properties["source_uri"]]}
    if question_id == "GQ-027":
        modalities = sorted({obj.properties["modality"] for obj in _artifact_objects(runtime, "SCN-004")})
        return {"refs": modalities, "evidence": [obj.properties["source_uri"] for obj in _artifact_objects(runtime, "SCN-004")]}
    if question_id == "GQ-028":
        artifacts = _artifact_objects(runtime)
        ok = all(obj.properties.get("source_uri") and obj.properties.get("raw_payload_embedded") is False for obj in artifacts)
        return {"value": bool(ok), "evidence": ["multimodal/artifact-index.json"]}
    if question_id == "GQ-029":
        artifacts = _artifact_objects(runtime)
        ok = all(obj.properties.get("source_asset_iri") and obj.properties.get("scenario_id") and obj.properties.get("event_time") and obj.properties.get("provenance") for obj in artifacts)
>>>>>>> origin/main
        return {"value": bool(ok), "evidence": ["multimodal/artifact-index.json"]}
    if question_id == "GQ-030":
        supported: list[str] = []
        for scenario_id in ("SCN-001", "SCN-002", "SCN-003", "SCN-004"):
<<<<<<< HEAD
            structured = any(
                obj.properties.get("scenario_id") == scenario_id
                for obj in runtime.list_objects()
                if obj.type in {"DrillingEquipment", "WorkOrder", "FailureEvent", "DowntimeEvent"}
            )
            non_tabular = bool(_artifact_objects(runtime, scenario_id))
            if structured and non_tabular:
                supported.append(scenario_id)
        return {
            "refs": supported,
            "evidence": ["maintenance/work_orders.csv", "multimodal/artifact-index.json"],
        }
=======
            structured = any(obj.properties.get("scenario_id") == scenario_id for obj in runtime.list_objects() if obj.type in {"DrillingEquipment", "WorkOrder", "FailureEvent", "DowntimeEvent"})
            non_tabular = bool(_artifact_objects(runtime, scenario_id))
            if structured and non_tabular:
                supported.append(scenario_id)
        return {"refs": supported, "evidence": ["maintenance/work_orders.csv", "multimodal/artifact-index.json"]}
>>>>>>> origin/main
    raise KeyError(f"Unsupported golden question: {question_id}")


def score_golden_questions(runtime, dataset_dir: Path) -> dict[str, Any]:
    questions = _read_json(FIXTURE_V02 / "tests/golden-questions.json")
    details: list[dict[str, Any]] = []
    passed = 0
    provenance_passed = 0

    for question in questions:
        answer = answer_golden_question(runtime, dataset_dir, question["id"])
        if "expected_refs" in question:
            actual = {str(value) for value in answer.get("refs", [])}
            expected = {str(value) for value in question["expected_refs"]}
            ok = expected.issubset(actual)
        else:
            actual_value = answer.get("value")
            expected_value = question["expected_value"]
            if isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
<<<<<<< HEAD
                ok = isinstance(actual_value, (int, float)) and math.isclose(
                    float(actual_value), float(expected_value), rel_tol=1e-9, abs_tol=1e-9
                )
=======
                ok = isinstance(actual_value, (int, float)) and math.isclose(float(actual_value), float(expected_value), rel_tol=1e-9, abs_tol=1e-9)
>>>>>>> origin/main
            else:
                ok = actual_value == expected_value
        evidence = [str(item) for item in answer.get("evidence", []) if str(item)]
        provenance_ok = bool(evidence)
        passed += int(ok)
        provenance_passed += int(provenance_ok)
        details.append(
            {
                "id": question["id"],
                "question": question["question"],
                "passed": ok,
                "provenance": provenance_ok,
                "answer": {key: value for key, value in answer.items() if key != "evidence"},
                "evidence": evidence,
            }
        )

    total = len(questions)
    return {
        "dataset": "cepio-synthetic-drilling",
        "dataset_version": "0.2.0",
        "test_stage": "deterministic_semantic_runtime",
        "passed": passed,
        "total": total,
        "accuracy": passed / total if total else 0.0,
        "provenance_passed": provenance_passed,
        "provenance_coverage": provenance_passed / total if total else 0.0,
        "thresholds": {"accuracy": 0.90, "provenance_coverage": 1.0},
        "gate_passed": (passed / total >= 0.90 and provenance_passed == total) if total else False,
        "details": details,
    }


<<<<<<< HEAD
def run_acceptance(
    output: Path, *, telemetry_points: int = 12000, waveform_samples: int = 2048, seed: int = 1701
) -> dict[str, Any]:
    generator = _load_v02_generator()
    generator.generate_multimodal_dataset(
        output, telemetry_points=telemetry_points, waveform_samples=waveform_samples, seed=seed
    )
=======
def run_acceptance(output: Path, *, telemetry_points: int = 12000, waveform_samples: int = 2048, seed: int = 1701) -> dict[str, Any]:
    generator = _load_v02_generator()
    generator.generate_multimodal_dataset(output, telemetry_points=telemetry_points, waveform_samples=waveform_samples, seed=seed)
>>>>>>> origin/main
    runtime = build_acceptance_runtime(output)
    report = score_golden_questions(runtime, output)
    report["runtime_counts"] = {
        "objects": len(runtime.list_objects()),
<<<<<<< HEAD
        "events": sum(
            len(runtime.events_for(obj.id))
            for obj in runtime.list_objects()
            if obj.type == "DrillingEquipment"
        ),
=======
        "events": sum(len(runtime.events_for(obj.id)) for obj in runtime.list_objects() if obj.type == "DrillingEquipment"),
>>>>>>> origin/main
        "artifacts": len(_artifact_objects(runtime)),
    }
    return report


def main() -> None:
<<<<<<< HEAD
    parser = argparse.ArgumentParser(
        description="Run CEPIO drilling v0.2 synthetic runtime acceptance test"
    )
=======
    parser = argparse.ArgumentParser(description="Run CEPIO drilling v0.2 synthetic runtime acceptance test")
>>>>>>> origin/main
    parser.add_argument("--output", type=Path, default=Path(".generated/drilling-v0.2-acceptance"))
    parser.add_argument("--telemetry-points", type=int, default=12000)
    parser.add_argument("--waveform-samples", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

<<<<<<< HEAD
    report = run_acceptance(
        args.output,
        telemetry_points=args.telemetry_points,
        waveform_samples=args.waveform_samples,
        seed=args.seed,
    )
=======
    report = run_acceptance(args.output, telemetry_points=args.telemetry_points, waveform_samples=args.waveform_samples, seed=args.seed)
>>>>>>> origin/main
    payload = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if not report["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
