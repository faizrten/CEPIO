from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_drilling_mvp_acceptance",
    ROOT / "scripts/run_drilling_mvp_acceptance.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _build(tmp_path: Path):
    generator = MODULE._load_v02_generator()
    dataset = tmp_path / "drilling-v0.2"
<<<<<<< HEAD
    generator.generate_multimodal_dataset(
        dataset, telemetry_points=6000, waveform_samples=2048, seed=1701
    )
=======
    generator.generate_multimodal_dataset(dataset, telemetry_points=6000, waveform_samples=2048, seed=1701)
>>>>>>> origin/main
    runtime = MODULE.build_acceptance_runtime(dataset)
    return dataset, runtime


def test_synthetic_drilling_v02_passes_runtime_golden_gate(tmp_path: Path):
    dataset, runtime = _build(tmp_path)
    report = MODULE.score_golden_questions(runtime, dataset)
    assert report["passed"] >= 27
    assert report["accuracy"] >= 0.90
    assert report["provenance_coverage"] == 1.0
    assert report["gate_passed"] is True


def test_synthetic_drilling_v02_is_queryable_through_public_api(tmp_path: Path, monkeypatch):
    _, runtime = _build(tmp_path)

    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    import cepio.api as legacy_api
    from cepio.public_api import app

    legacy_api.runtime = runtime
    headers = {
        "X-CEPIO-Dev-Actor": "synthetic-test",
        "X-CEPIO-Dev-Roles": "cepio_admin,operator,graph_analyst,auditor",
    }
    client = TestClient(app)

    response = client.get("/api/v1/objects/rig-07", headers=headers)
    assert response.status_code == 200
    assert response.json()["type"] == "OperatingRig"

    query = client.post(
        "/api/v1/query/objects",
        headers=headers,
<<<<<<< HEAD
        json={
            "object_type": "DrillingEquipment",
            "predicates": [{"property": "equipment_type", "operator": "eq", "value": "MudPump"}],
            "limit": 20,
        },
=======
        json={"object_type": "DrillingEquipment", "predicates": [{"property": "equipment_type", "operator": "eq", "value": "MudPump"}], "limit": 20},
>>>>>>> origin/main
    )
    assert query.status_code == 200
    ids = {item["id"] for item in query.json()["items"]}
    assert {"rig-07-mud-pump-01", "rig-12-mud-pump-02"}.issubset(ids)
