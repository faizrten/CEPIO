from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "extend_drilling_mvp_multimodal_v02",
    ROOT / "scripts/extend_drilling_mvp_multimodal_v02.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
generate_multimodal_dataset = MODULE.generate_multimodal_dataset

FIXTURE = ROOT / "mvp/datasets/drilling-v0.2"


def test_v02_contract_extends_v01_without_replacing_it():
    schema = json.loads((FIXTURE / "schema.json").read_text(encoding="utf-8"))
    golden = json.loads((FIXTURE / "tests/golden-questions.json").read_text(encoding="utf-8"))
    contract = json.loads(
        (FIXTURE / "ground-truth/artifact-contract.json").read_text(encoding="utf-8")
    )

    assert schema["inherits"] == "drilling-v0.1"
    assert len(golden) == 30
    assert golden[:20] == json.loads(
        (ROOT / "mvp/datasets/drilling-v0.1/tests/golden-questions.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(contract["required_modalities"]) == {
        "document",
        "inspection_image",
        "engineering_diagram",
        "geospatial",
        "high_frequency_signal",
    }
    assert schema["artifact_policy"]["store_raw_payload_in_ontology"] is False


def test_v02_generator_creates_bound_multimodal_evidence(tmp_path: Path):
    manifest = generate_multimodal_dataset(
        tmp_path,
        telemetry_points=500,
        waveform_samples=128,
        seed=1701,
    )
    expected = {
        "document": 8,
        "inspection_image": 4,
        "engineering_diagram": 4,
        "geospatial": 1,
        "high_frequency_signal": 4,
    }
    assert manifest["version"] == "0.2.0"
    assert manifest["inherits"] == "drilling-v0.1"
    assert manifest["multimodal"]["modalities"] == expected

    index = json.loads((tmp_path / "multimodal/artifact-index.json").read_text(encoding="utf-8"))
    assert len(index["artifacts"]) == 21
    for artifact in index["artifacts"]:
        assert artifact["canonical_iri"].startswith("cepio://")
        assert artifact["scenario_id"] in {"SCN-001", "SCN-002", "SCN-003", "SCN-004"}
        assert artifact["event_time"].endswith("Z")
        assert artifact["provenance"]["dataset_version"] == "0.2.0"
        assert (tmp_path / artifact["path"]).exists()

    ppm = tmp_path / "images/inspection/scn-001-bearing_discoloration.ppm"
    assert ppm.read_text(encoding="utf-8").startswith("P3\n96 64\n255\n")

    svg = (tmp_path / "engineering/diagrams/scn-003-context.svg").read_text(encoding="utf-8")
    assert "annular sealing element" in svg
    assert "SCN-003" in svg

    geo = json.loads((tmp_path / "geospatial/rig-well-context.geojson").read_text(encoding="utf-8"))
    assert len(geo["features"]) == 14
    assert {
        feature["id"] for feature in geo["features"] if feature["geometry"]["type"] == "Point"
    } >= {"rig-07", "rig-12", "rig-21", "well-02", "well-05", "well-08"}

    waveform = tmp_path / "signals/high-frequency/scn-001-vibration_velocity.csv"
    with waveform.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 128
    assert rows[0]["unit"] == "mm/s"


def test_v02_generation_is_deterministic_for_source_artifacts(tmp_path: Path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    generate_multimodal_dataset(first, telemetry_points=200, waveform_samples=128, seed=1701)
    generate_multimodal_dataset(second, telemetry_points=200, waveform_samples=128, seed=1701)

    paths = [
        "multimodal/artifact-index.json",
        "geospatial/rig-well-context.geojson",
        "images/inspection/scn-004-valve_seat_wear.ppm",
        "engineering/diagrams/scn-002-context.svg",
        "signals/high-frequency/scn-003-pressure_transient.csv",
        "documents/inspection-reports/scn-001-inspection.md",
    ]
    for path in paths:
        assert (first / path).read_bytes() == (second / path).read_bytes()
