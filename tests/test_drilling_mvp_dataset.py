from __future__ import annotations

import csv
import json
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("generate_drilling_mvp_dataset", ROOT / "scripts/generate_drilling_mvp_dataset.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
generate_dataset = MODULE.generate_dataset

FIXTURE = ROOT / "mvp/datasets/drilling-v0.1"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_ground_truth_contract_is_complete():
    scenarios = json.loads((FIXTURE / "ground-truth/scenarios.json").read_text(encoding="utf-8"))
    golden = json.loads((FIXTURE / "tests/golden-questions.json").read_text(encoding="utf-8"))
    aliases = json.loads((FIXTURE / "ground-truth/entity-resolution.json").read_text(encoding="utf-8"))
    assert len(scenarios) == 4
    assert len(golden) == 20
    assert {item["scenario_id"] for item in scenarios} == {"SCN-001", "SCN-002", "SCN-003", "SCN-004"}
    assert len({alias for item in aliases for alias in item["aliases"].values()}) == sum(len(item["aliases"]) for item in aliases)


def test_generator_is_deterministic_and_links_scenarios(tmp_path: Path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    manifest_a = generate_dataset(first, telemetry_points=500, seed=1701)
    manifest_b = generate_dataset(second, telemetry_points=500, seed=1701)
    assert manifest_a == manifest_b
    assert (first / "telemetry/telemetry.csv").read_bytes() == (second / "telemetry/telemetry.csv").read_bytes()
    assert manifest_a["counts"]["rigs"] == 3
    assert manifest_a["counts"]["wells"] == 10
    assert manifest_a["counts"]["equipment"] == 18
    assert manifest_a["counts"]["telemetry"] == 500
    assert manifest_a["counts"]["failure_events"] == 3

    npt = {row["scenario_id"]: row for row in _read_csv(first / "operations/npt_events.csv")}
    assert float(npt["SCN-001"]["duration_hours"]) == 4.2
    assert float(npt["SCN-003"]["duration_hours"]) == 1.5
    assert float(npt["SCN-004"]["duration_hours"]) == 2.1

    failures = {row["scenario_id"]: row for row in _read_csv(first / "reliability/failure_events.csv")}
    assert failures["SCN-001"]["failure_event_id"] == "FAIL-001"

    work = {row["scenario_id"]: row for row in _read_csv(first / "maintenance/work_orders.csv")}
    assert work["SCN-001"]["work_order_id"] == "WO-0071"
    assert work["SCN-002"]["status"] == "open"


def test_schema_uses_existing_cepio_semantics():
    schema = json.loads((FIXTURE / "schema.json").read_text(encoding="utf-8"))
    alignment = schema["ontology_alignment"]
    assert alignment["rig"].endswith("drilling#OperatingRig")
    assert alignment["equipment"].endswith("drilling#DrillingEquipment")
    assert alignment["work_order"].endswith("industrial#WorkOrder")
    assert alignment["failure_event"].endswith("reliability#FailureEvent")
