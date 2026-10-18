from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

DATASET_VERSION = "0.1.0"
DEFAULT_SEED = 1701
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
RIGS = ["rig-07", "rig-12", "rig-21"]
EQUIPMENT_BLUEPRINT = [
    ("mud-pump-01", "MudPump", "National", "12-P-160"),
    ("mud-pump-02", "MudPump", "National", "12-P-160"),
    ("top-drive-01", "TopDrive", "NOV", "TDS-11SA"),
    ("bop-01", "BlowoutPreventer", "Cameron", "18-3/4-15K"),
    ("drawworks-01", "Drawworks", "NOV", "ADS-10Q"),
    ("generator-01", "Generator", "CAT", "3512C"),
]
SIGNALS = {
<<<<<<< HEAD
    "MudPump": [
        ("vibration-rms", "mm/s"),
        ("bearing-temperature", "degC"),
        ("discharge-pressure", "psi"),
        ("stroke-rate", "spm"),
    ],
    "TopDrive": [
        ("motor-temperature", "degC"),
        ("coolant-temperature", "degC"),
        ("torque", "kN.m"),
    ],
=======
    "MudPump": [("vibration-rms", "mm/s"), ("bearing-temperature", "degC"), ("discharge-pressure", "psi"), ("stroke-rate", "spm")],
    "TopDrive": [("motor-temperature", "degC"), ("coolant-temperature", "degC"), ("torque", "kN.m")],
>>>>>>> origin/main
    "BlowoutPreventer": [("bop-test-pressure", "psi"), ("pressure-decay-rate", "psi/min")],
    "Drawworks": [("motor-current", "A"), ("brake-temperature", "degC")],
    "Generator": [("load", "%"), ("oil-pressure", "psi")],
}


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _iso(dt: datetime | None) -> str:
    return "" if dt is None else dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _equipment_id(rig_id: str, suffix: str) -> str:
    return f"{rig_id}-{suffix}"


def _asset_iri(rig_id: str, suffix: str) -> str:
    return f"cepio://asset/{rig_id}/{suffix}"


def _scenario_for(equipment_id: str) -> str:
    return {
        "rig-07-mud-pump-01": "SCN-001",
        "rig-12-top-drive-01": "SCN-002",
        "rig-21-bop-01": "SCN-003",
        "rig-12-mud-pump-02": "SCN-004",
    }.get(equipment_id, "")


<<<<<<< HEAD
def _telemetry_value(
    signal: str, timestamp: datetime, scenario_id: str, rng: random.Random
) -> float:
=======
def _telemetry_value(signal: str, timestamp: datetime, scenario_id: str, rng: random.Random) -> float:
>>>>>>> origin/main
    day = (timestamp - START).total_seconds() / 86400.0
    noise = rng.gauss(0, 1)
    baselines = {
        "vibration-rms": (3.2, 0.15),
        "bearing-temperature": (68.0, 0.8),
        "discharge-pressure": (3100.0, 20.0),
        "stroke-rate": (108.0, 1.5),
        "motor-temperature": (72.0, 0.8),
        "coolant-temperature": (54.0, 0.6),
        "torque": (22.0, 0.6),
        "bop-test-pressure": (5000.0, 8.0),
        "pressure-decay-rate": (2.0, 0.25),
        "motor-current": (420.0, 6.0),
        "brake-temperature": (63.0, 0.8),
        "load": (67.0, 2.0),
        "oil-pressure": (58.0, 0.8),
    }
    base, sigma = baselines[signal]
    value = base + noise * sigma

    if scenario_id == "SCN-001" and 20 <= day <= 35:
        progress = (day - 20) / 15
        if signal == "vibration-rms":
            value += 5.5 * progress
        elif signal == "bearing-temperature":
            value += 18.0 * progress
    elif scenario_id == "SCN-002" and day >= 45:
        progress = min((day - 45) / 20, 1.0)
        if signal == "motor-temperature":
            value += 12.0 * progress
        elif signal == "coolant-temperature":
            value += 9.0 * progress
    elif scenario_id == "SCN-003" and 54 <= day <= 56:
        if signal == "bop-test-pressure":
            value -= 120.0 * max(day - 54, 0)
        elif signal == "pressure-decay-rate":
            value += 7.0 * max(day - 54, 0)
    elif scenario_id == "SCN-004" and 64 <= day <= 70:
        if signal == "discharge-pressure":
            value += 320.0 * math.sin(day * 8.0)
        elif signal == "stroke-rate":
            value += 6.0 * math.sin(day * 5.0)

    # Repairs normalize realized failures after the scenario window.
    if scenario_id == "SCN-001" and day > 35.25:
        value = base + noise * sigma
    if scenario_id == "SCN-003" and day > 56.25:
        value = base + noise * sigma
    if scenario_id == "SCN-004" and day > 70.2:
        value = base + noise * sigma

    return round(value, 3)


def generate_dataset(output: Path, telemetry_points: int = 12000, seed: int = DEFAULT_SEED) -> dict:
    rng = random.Random(seed)
    output = Path(output)
    counts: dict[str, int] = {}

    rigs = [
<<<<<<< HEAD
        {
            "rig_id": rig,
            "canonical_iri": f"cepio://asset/{rig}",
            "name": f"CEPIO Test Rig {rig.split('-')[1]}",
            "rig_type": "JackUpRig",
            "status": "operational",
        }
=======
        {"rig_id": rig, "canonical_iri": f"cepio://asset/{rig}", "name": f"CEPIO Test Rig {rig.split('-')[1]}", "rig_type": "JackUpRig", "status": "operational"}
>>>>>>> origin/main
        for rig in RIGS
    ]
    counts["rigs"] = _write_csv(output / "master-data/rigs.csv", list(rigs[0]), rigs)

    wells = []
    for idx in range(10):
        rig = RIGS[idx % len(RIGS)]
<<<<<<< HEAD
        well_id = f"well-{idx + 1:02d}"
        wells.append(
            {
                "well_id": well_id,
                "canonical_iri": f"cepio://well/{well_id}",
                "name": f"CEPIO-W-{idx + 1:02d}",
                "rig_id": rig,
                "status": "active" if idx < 3 else "completed",
            }
        )
=======
        well_id = f"well-{idx+1:02d}"
        wells.append({"well_id": well_id, "canonical_iri": f"cepio://well/{well_id}", "name": f"CEPIO-W-{idx+1:02d}", "rig_id": rig, "status": "active" if idx < 3 else "completed"})
>>>>>>> origin/main
    counts["wells"] = _write_csv(output / "operations/wells.csv", list(wells[0]), wells)

    equipment = []
    for rig in RIGS:
        for suffix, equipment_type, manufacturer, model in EQUIPMENT_BLUEPRINT:
            eid = _equipment_id(rig, suffix)
<<<<<<< HEAD
            equipment.append(
                {
                    "equipment_id": eid,
                    "canonical_iri": _asset_iri(rig, suffix),
                    "rig_id": rig,
                    "equipment_type": equipment_type,
                    "name": suffix.replace("-", " ").title(),
                    "manufacturer": manufacturer,
                    "model": model,
                    "criticality": "A"
                    if equipment_type in {"MudPump", "TopDrive", "BlowoutPreventer"}
                    else "B",
                }
            )
    counts["equipment"] = _write_csv(
        output / "master-data/equipment.csv", list(equipment[0]), equipment
    )
=======
            equipment.append({
                "equipment_id": eid,
                "canonical_iri": _asset_iri(rig, suffix),
                "rig_id": rig,
                "equipment_type": equipment_type,
                "name": suffix.replace("-", " ").title(),
                "manufacturer": manufacturer,
                "model": model,
                "criticality": "A" if equipment_type in {"MudPump", "TopDrive", "BlowoutPreventer"} else "B",
            })
    counts["equipment"] = _write_csv(output / "master-data/equipment.csv", list(equipment[0]), equipment)
>>>>>>> origin/main

    components = []
    for item in equipment:
        for n, component_type in enumerate(["drive-end-bearing", "motor", "valve", "seal"], 1):
            cid = f"{item['equipment_id']}-c{n:02d}"
<<<<<<< HEAD
            components.append(
                {
                    "component_id": cid,
                    "canonical_iri": f"{item['canonical_iri']}/component/{n:02d}",
                    "equipment_id": item["equipment_id"],
                    "component_type": component_type,
                    "name": component_type.replace("-", " ").title(),
                }
            )
    counts["components"] = _write_csv(
        output / "master-data/components.csv", list(components[0]), components
    )
=======
            components.append({"component_id": cid, "canonical_iri": f"{item['canonical_iri']}/component/{n:02d}", "equipment_id": item["equipment_id"], "component_type": component_type, "name": component_type.replace("-", " ").title()})
    counts["components"] = _write_csv(output / "master-data/components.csv", list(components[0]), components)
>>>>>>> origin/main

    sensors = []
    for item in equipment:
        for signal, unit in SIGNALS[item["equipment_type"]]:
            sid = f"{item['equipment_id']}-{signal}"
            source_tag = sid.upper().replace("-", "_")
            if sid == "rig-07-mud-pump-01-vibration-rms":
                source_tag = "MP-001.VIB_RMS"
<<<<<<< HEAD
            sensors.append(
                {
                    "sensor_id": sid,
                    "canonical_iri": f"cepio://sensor/{sid}",
                    "equipment_id": item["equipment_id"],
                    "signal_type": signal.replace("-", "_"),
                    "unit": unit,
                    "source_tag": source_tag,
                }
            )
    counts["sensors"] = _write_csv(output / "master-data/sensors.csv", list(sensors[0]), sensors)

    roles = [
        "Rig Manager",
        "Toolpusher",
        "Driller",
        "Maintenance Superintendent",
        "Mechanical Technician",
        "Electrical Technician",
        "HSE Advisor",
    ]
    personnel = []
    for idx in range(21):
        rig = RIGS[idx % 3]
        personnel.append(
            {
                "person_id": f"P-{idx + 1:03d}",
                "name": f"Synthetic Person {idx + 1:03d}",
                "role": roles[idx % len(roles)],
                "rig_id": rig,
            }
        )
    counts["personnel"] = _write_csv(
        output / "master-data/personnel.csv", list(personnel[0]), personnel
    )
=======
            sensors.append({"sensor_id": sid, "canonical_iri": f"cepio://sensor/{sid}", "equipment_id": item["equipment_id"], "signal_type": signal.replace("-", "_"), "unit": unit, "source_tag": source_tag})
    counts["sensors"] = _write_csv(output / "master-data/sensors.csv", list(sensors[0]), sensors)

    roles = ["Rig Manager", "Toolpusher", "Driller", "Maintenance Superintendent", "Mechanical Technician", "Electrical Technician", "HSE Advisor"]
    personnel = []
    for idx in range(21):
        rig = RIGS[idx % 3]
        personnel.append({"person_id": f"P-{idx+1:03d}", "name": f"Synthetic Person {idx+1:03d}", "role": roles[idx % len(roles)], "rig_id": rig})
    counts["personnel"] = _write_csv(output / "master-data/personnel.csv", list(personnel[0]), personnel)
>>>>>>> origin/main

    activities = []
    for idx in range(240):
        rig = RIGS[idx % 3]
        well = wells[idx % len(wells)]["well_id"]
        start = START + timedelta(hours=idx * 6)
<<<<<<< HEAD
        activities.append(
            {
                "activity_id": f"ACT-{idx + 1:04d}",
                "rig_id": rig,
                "well_id": well,
                "classification": ["DRILL", "TRIP", "CIRCULATE", "MAINTENANCE"][idx % 4],
                "start_time": _iso(start),
                "end_time": _iso(start + timedelta(hours=5, minutes=30)),
            }
        )
    counts["activities"] = _write_csv(
        output / "operations/activities.csv", list(activities[0]), activities
    )

    npt_specs = [
        (
            "NPT-001",
            "rig-07",
            "well-01",
            "rig-07-mud-pump-01",
            35.0,
            4.2,
            "equipment_failure",
            "SCN-001",
        ),
        (
            "NPT-003",
            "rig-21",
            "well-03",
            "rig-21-bop-01",
            56.0,
            1.5,
            "well_control_test_failure",
            "SCN-003",
        ),
        (
            "NPT-004",
            "rig-12",
            "well-02",
            "rig-12-mud-pump-02",
            70.0,
            2.1,
            "equipment_failure",
            "SCN-004",
        ),
=======
        activities.append({"activity_id": f"ACT-{idx+1:04d}", "rig_id": rig, "well_id": well, "classification": ["DRILL", "TRIP", "CIRCULATE", "MAINTENANCE"][idx % 4], "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=5, minutes=30))})
    counts["activities"] = _write_csv(output / "operations/activities.csv", list(activities[0]), activities)

    npt_specs = [
        ("NPT-001", "rig-07", "well-01", "rig-07-mud-pump-01", 35.0, 4.2, "equipment_failure", "SCN-001"),
        ("NPT-003", "rig-21", "well-03", "rig-21-bop-01", 56.0, 1.5, "well_control_test_failure", "SCN-003"),
        ("NPT-004", "rig-12", "well-02", "rig-12-mud-pump-02", 70.0, 2.1, "equipment_failure", "SCN-004"),
>>>>>>> origin/main
    ]
    npt_events = []
    for event_id, rig, well, equipment_id, day, duration, category, scenario in npt_specs:
        start = START + timedelta(days=day)
<<<<<<< HEAD
        npt_events.append(
            {
                "npt_event_id": event_id,
                "rig_id": rig,
                "well_id": well,
                "equipment_id": equipment_id,
                "start_time": _iso(start),
                "end_time": _iso(start + timedelta(hours=duration)),
                "duration_hours": duration,
                "category": category,
                "scenario_id": scenario,
            }
        )
    counts["npt_events"] = _write_csv(
        output / "operations/npt_events.csv", list(npt_events[0]), npt_events
    )

    failure_events = [
        {
            "failure_event_id": "FAIL-001",
            "equipment_id": "rig-07-mud-pump-01",
            "timestamp": _iso(START + timedelta(days=35.0)),
            "failure_mode": "drive-end-bearing-degradation",
            "scenario_id": "SCN-001",
        },
        {
            "failure_event_id": "FAIL-003",
            "equipment_id": "rig-21-bop-01",
            "timestamp": _iso(START + timedelta(days=56.0)),
            "failure_mode": "annular-seal-leakage",
            "scenario_id": "SCN-003",
        },
        {
            "failure_event_id": "FAIL-004",
            "equipment_id": "rig-12-mud-pump-02",
            "timestamp": _iso(START + timedelta(days=70.0)),
            "failure_mode": "discharge-valve-sticking",
            "scenario_id": "SCN-004",
        },
    ]
    counts["failure_events"] = _write_csv(
        output / "reliability/failure_events.csv", list(failure_events[0]), failure_events
    )

    work_specs = [
        (
            "WO-0071",
            "rig-07-mud-pump-01",
            "completed",
            "P1",
            34.8,
            35.25,
            "Replace drive-end bearing",
            "SCN-001",
        ),
        (
            "WO-0124",
            "rig-12-top-drive-01",
            "open",
            "P2",
            62.0,
            None,
            "Inspect and clean top-drive cooling loop",
            "SCN-002",
        ),
        (
            "WO-0219",
            "rig-21-bop-01",
            "completed",
            "P1",
            56.0,
            56.25,
            "Replace annular sealing element and retest",
            "SCN-003",
        ),
        (
            "WO-0133",
            "rig-12-mud-pump-02",
            "completed",
            "P1",
            70.0,
            70.2,
            "Replace discharge-valve assembly",
            "SCN-004",
        ),
    ]
    work_orders = []
    maintenance_events = []
    for idx, (
        wo,
        equipment_id,
        status,
        priority,
        created_day,
        completed_day,
        description,
        scenario,
    ) in enumerate(work_specs, 1):
        created = START + timedelta(days=created_day)
        completed = None if completed_day is None else START + timedelta(days=completed_day)
        work_orders.append(
            {
                "work_order_id": wo,
                "equipment_id": equipment_id,
                "status": status,
                "priority": priority,
                "created_time": _iso(created),
                "completed_time": _iso(completed),
                "description": description,
                "scenario_id": scenario,
            }
        )
        maintenance_events.append(
            {
                "maintenance_event_id": f"ME-{idx:03d}",
                "equipment_id": equipment_id,
                "work_order_id": wo,
                "event_type": "inspection" if completed is None else "repair_completed",
                "timestamp": _iso(created if completed is None else completed),
                "scenario_id": scenario,
            }
        )
    counts["work_orders"] = _write_csv(
        output / "maintenance/work_orders.csv", list(work_orders[0]), work_orders
    )
    counts["maintenance_events"] = _write_csv(
        output / "maintenance/maintenance_events.csv",
        list(maintenance_events[0]),
        maintenance_events,
    )
=======
        npt_events.append({"npt_event_id": event_id, "rig_id": rig, "well_id": well, "equipment_id": equipment_id, "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=duration)), "duration_hours": duration, "category": category, "scenario_id": scenario})
    counts["npt_events"] = _write_csv(output / "operations/npt_events.csv", list(npt_events[0]), npt_events)

    failure_events = [
        {"failure_event_id": "FAIL-001", "equipment_id": "rig-07-mud-pump-01", "timestamp": _iso(START + timedelta(days=35.0)), "failure_mode": "drive-end-bearing-degradation", "scenario_id": "SCN-001"},
        {"failure_event_id": "FAIL-003", "equipment_id": "rig-21-bop-01", "timestamp": _iso(START + timedelta(days=56.0)), "failure_mode": "annular-seal-leakage", "scenario_id": "SCN-003"},
        {"failure_event_id": "FAIL-004", "equipment_id": "rig-12-mud-pump-02", "timestamp": _iso(START + timedelta(days=70.0)), "failure_mode": "discharge-valve-sticking", "scenario_id": "SCN-004"},
    ]
    counts["failure_events"] = _write_csv(output / "reliability/failure_events.csv", list(failure_events[0]), failure_events)

    work_specs = [
        ("WO-0071", "rig-07-mud-pump-01", "completed", "P1", 34.8, 35.25, "Replace drive-end bearing", "SCN-001"),
        ("WO-0124", "rig-12-top-drive-01", "open", "P2", 62.0, None, "Inspect and clean top-drive cooling loop", "SCN-002"),
        ("WO-0219", "rig-21-bop-01", "completed", "P1", 56.0, 56.25, "Replace annular sealing element and retest", "SCN-003"),
        ("WO-0133", "rig-12-mud-pump-02", "completed", "P1", 70.0, 70.2, "Replace discharge-valve assembly", "SCN-004"),
    ]
    work_orders = []
    maintenance_events = []
    for idx, (wo, equipment_id, status, priority, created_day, completed_day, description, scenario) in enumerate(work_specs, 1):
        created = START + timedelta(days=created_day)
        completed = None if completed_day is None else START + timedelta(days=completed_day)
        work_orders.append({"work_order_id": wo, "equipment_id": equipment_id, "status": status, "priority": priority, "created_time": _iso(created), "completed_time": _iso(completed), "description": description, "scenario_id": scenario})
        maintenance_events.append({"maintenance_event_id": f"ME-{idx:03d}", "equipment_id": equipment_id, "work_order_id": wo, "event_type": "inspection" if completed is None else "repair_completed", "timestamp": _iso(created if completed is None else completed), "scenario_id": scenario})
    counts["work_orders"] = _write_csv(output / "maintenance/work_orders.csv", list(work_orders[0]), work_orders)
    counts["maintenance_events"] = _write_csv(output / "maintenance/maintenance_events.csv", list(maintenance_events[0]), maintenance_events)
>>>>>>> origin/main

    telemetry_path = output / "telemetry/telemetry.csv"
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp", "sensor_id", "equipment_id", "value", "unit", "quality", "scenario_id"]
    with telemetry_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for idx in range(telemetry_points):
            sensor = sensors[idx % len(sensors)]
            timestamp = START + timedelta(days=(90.0 * idx / max(telemetry_points - 1, 1)))
            scenario = _scenario_for(sensor["equipment_id"])
<<<<<<< HEAD
            writer.writerow(
                {
                    "timestamp": _iso(timestamp),
                    "sensor_id": sensor["sensor_id"],
                    "equipment_id": sensor["equipment_id"],
                    "value": _telemetry_value(
                        sensor["signal_type"].replace("_", "-"), timestamp, scenario, rng
                    ),
                    "unit": sensor["unit"],
                    "quality": "good",
                    "scenario_id": scenario,
                }
            )
=======
            writer.writerow({
                "timestamp": _iso(timestamp),
                "sensor_id": sensor["sensor_id"],
                "equipment_id": sensor["equipment_id"],
                "value": _telemetry_value(sensor["signal_type"].replace("_", "-"), timestamp, scenario, rng),
                "unit": sensor["unit"],
                "quality": "good",
                "scenario_id": scenario,
            })
>>>>>>> origin/main
    counts["telemetry"] = telemetry_points

    manifest = {
        "dataset": "cepio-synthetic-drilling",
        "version": DATASET_VERSION,
        "seed": seed,
        "generated_at": "deterministic-fixture",
        "counts": counts,
        "ground_truth": {
            "scenarios": "ground-truth/scenarios.json",
            "entity_resolution": "ground-truth/entity-resolution.json",
<<<<<<< HEAD
            "golden_questions": "tests/golden-questions.json",
        },
=======
            "golden_questions": "tests/golden-questions.json"
        }
>>>>>>> origin/main
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
<<<<<<< HEAD
    parser = argparse.ArgumentParser(
        description="Generate CEPIO Synthetic Industrial Dataset — Drilling v0.1"
    )
=======
    parser = argparse.ArgumentParser(description="Generate CEPIO Synthetic Industrial Dataset — Drilling v0.1")
>>>>>>> origin/main
    parser.add_argument("--output", type=Path, default=Path(".generated/drilling-v0.1"))
    parser.add_argument("--telemetry-points", type=int, default=12000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    manifest = generate_dataset(args.output, telemetry_points=args.telemetry_points, seed=args.seed)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
