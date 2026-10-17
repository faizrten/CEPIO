from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATASET_VERSION = "0.2.0"
DEFAULT_SEED = 1701
START = datetime(2026, 1, 1, tzinfo=timezone.utc)

SCENARIOS = {
    "SCN-001": {
        "equipment_id": "rig-07-mud-pump-01",
        "canonical_iri": "cepio://asset/rig-07/mud-pump-01",
        "event_day": 35.0,
        "signal": "vibration_velocity",
        "unit": "mm/s",
        "base_frequency_hz": 29.0,
        "fault_frequency_hz": 116.0,
        "document_claim": "Drive-end bearing vibration and temperature increased before failure.",
        "image_feature": "bearing_discoloration",
        "diagram_component": "drive-end bearing",
    },
    "SCN-002": {
        "equipment_id": "rig-12-top-drive-01",
        "canonical_iri": "cepio://asset/rig-12/top-drive-01",
        "event_day": 62.0,
        "signal": "motor_current",
        "unit": "A",
        "base_frequency_hz": 50.0,
        "fault_frequency_hz": 100.0,
        "document_claim": "Cooling-loop fouling is suspected; preventive work remains open and no NPT has occurred.",
        "image_feature": "cooling_fin_fouling",
        "diagram_component": "cooling loop",
    },
    "SCN-003": {
        "equipment_id": "rig-21-bop-01",
        "canonical_iri": "cepio://asset/rig-21/bop-01",
        "event_day": 56.0,
        "signal": "pressure_transient",
        "unit": "psi",
        "base_frequency_hz": 4.0,
        "fault_frequency_hz": 17.0,
        "document_claim": "BOP pressure decay exceeded the synthetic acceptance threshold before sealing-element replacement.",
        "image_feature": "seal_surface_damage",
        "diagram_component": "annular sealing element",
    },
    "SCN-004": {
        "equipment_id": "rig-12-mud-pump-02",
        "canonical_iri": "cepio://asset/rig-12/mud-pump-02",
        "event_day": 70.0,
        "signal": "discharge_pressure_dynamic",
        "unit": "psi",
        "base_frequency_hz": 2.5,
        "fault_frequency_hz": 11.0,
        "document_claim": "Intermittent discharge-valve sticking produced pressure excursions and 2.1 hours of NPT.",
        "image_feature": "valve_seat_wear",
        "diagram_component": "discharge valve",
    },
}


def _load_v01():
    sibling = Path(__file__).resolve().with_name("generate_drilling_mvp_dataset.py")
    spec = importlib.util.spec_from_file_location("generate_drilling_mvp_dataset", sibling)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load v0.1 generator: {sibling}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_ppm(path: Path, scenario_id: str, width: int = 96, height: int = 64) -> None:
    """Write a deterministic synthetic inspection image using portable pixmap P3."""
    scenario_index = int(scenario_id.split("-")[1])
    lines = ["P3", f"{width} {height}", "255"]
    for y in range(height):
        row: list[str] = []
        for x in range(width):
            radial = math.sqrt((x - width * 0.5) ** 2 + (y - height * 0.5) ** 2)
            defect = 1 if radial < 10 + scenario_index * 2 else 0
            texture = (x * 7 + y * 11 + scenario_index * 17) % 35
            r = min(255, 95 + texture + defect * 105)
            g = min(255, 100 + texture // 2 + defect * 25)
            b = min(255, 105 + texture // 3)
            row.extend([str(r), str(g), str(b)])
        lines.append(" ".join(row))
    _write_text(path, "\n".join(lines) + "\n")


def _write_svg(path: Path, scenario_id: str, component: str, canonical_iri: str) -> None:
    rig_id = "/".join(canonical_iri.split("/")[3:4])
    asset_id = canonical_iri.split("/")[-1]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="360" viewBox="0 0 900 360">
  <title>CEPIO synthetic engineering context {scenario_id}</title>
  <desc>Source-neutral schematic linking rig, equipment, component, signal, event and work order.</desc>
  <rect x="20" y="130" width="125" height="70" rx="8" fill="none" stroke="black"/>
  <text x="82" y="160" text-anchor="middle">Rig</text>
  <text x="82" y="180" text-anchor="middle">{rig_id}</text>
  <rect x="195" y="130" width="150" height="70" rx="8" fill="none" stroke="black"/>
  <text x="270" y="160" text-anchor="middle">Equipment</text>
  <text x="270" y="180" text-anchor="middle">{asset_id}</text>
  <rect x="395" y="130" width="160" height="70" rx="8" fill="none" stroke="black" stroke-width="3"/>
  <text x="475" y="160" text-anchor="middle">Component</text>
  <text x="475" y="180" text-anchor="middle">{component}</text>
  <rect x="605" y="55" width="150" height="60" rx="8" fill="none" stroke="black"/>
  <text x="680" y="90" text-anchor="middle">Condition signal</text>
  <rect x="605" y="145" width="150" height="60" rx="8" fill="none" stroke="black"/>
  <text x="680" y="180" text-anchor="middle">{scenario_id}</text>
  <rect x="605" y="235" width="150" height="60" rx="8" fill="none" stroke="black"/>
  <text x="680" y="270" text-anchor="middle">Work order</text>
  <path d="M145 165 H195 M345 165 H395 M555 165 H605 M555 150 C585 130 585 85 605 85 M555 180 C585 210 585 265 605 265" fill="none" stroke="black" marker-end="url(#a)"/>
  <defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z"/></marker></defs>
</svg>'''
    _write_text(path, svg + "\n")


def _artifact(scenario_id: str, modality: str, relpath: Path, mime_type: str, spec: dict, event_time: datetime, claims: list[str]) -> dict[str, object]:
    return {
        "artifact_id": f"ART-{scenario_id}-{modality}-{relpath.stem}",
        "scenario_id": scenario_id,
        "modality": modality,
        "path": relpath.as_posix(),
        "mime_type": mime_type,
        "canonical_iri": spec["canonical_iri"],
        "equipment_id": spec["equipment_id"],
        "event_time": _iso(event_time),
        "ground_truth_claims": claims,
        "provenance": {"source": "cepio-synthetic-generator", "dataset_version": DATASET_VERSION},
    }


def _write_documents(output: Path) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    for scenario_id, spec in SCENARIOS.items():
        event_time = START + timedelta(days=float(spec["event_day"]))
        inspection_path = Path("documents/inspection-reports") / f"{scenario_id.lower()}-inspection.md"
        ddr_path = Path("documents/daily-drilling-reports") / f"{scenario_id.lower()}-ddr.md"
        inspection = f"""# Synthetic Inspection Report — {scenario_id}\n\nAsset: `{spec['canonical_iri']}`\nInspection time: {_iso(event_time - timedelta(hours=2))}\n\n## Observation\n{spec['document_claim']}\n\n## Disposition\nCorrelate this observation with telemetry, work history and event records before making an operational decision.\n\nSynthetic fixture only; no customer or OEM data.\n"""
        ddr = f"""# Synthetic Daily Drilling Report — {scenario_id}\n\nEquipment: `{spec['equipment_id']}`\nEvent time: {_iso(event_time)}\n\nOperations note: {spec['document_claim']}\n\nSource-system naming is intentionally distinct from the CEPIO canonical identifier.\n"""
        _write_text(output / inspection_path, inspection)
        _write_text(output / ddr_path, ddr)
        artifacts.extend([
            _artifact(scenario_id, "document", inspection_path, "text/markdown", spec, event_time - timedelta(hours=2), ["inspection_observation", "asset_identity"]),
            _artifact(scenario_id, "document", ddr_path, "text/markdown", spec, event_time, ["operations_context", "event_time"]),
        ])
    return artifacts


def _write_geojson(output: Path) -> list[dict[str, object]]:
    rig_coords = {"rig-07": (50.10, 26.55), "rig-12": (50.34, 26.72), "rig-21": (50.58, 26.43)}
    features: list[dict[str, object]] = []
    for rig_id, (lon, lat) in rig_coords.items():
        features.append({"type": "Feature", "id": rig_id, "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"entity_type": "OperatingRig", "canonical_iri": f"cepio://asset/{rig_id}"}})
    for idx in range(10):
        rig_id = ["rig-07", "rig-12", "rig-21"][idx % 3]
        lon, lat = rig_coords[rig_id]
        well_id = f"well-{idx + 1:02d}"
        features.append({"type": "Feature", "id": well_id, "geometry": {"type": "Point", "coordinates": [round(lon + 0.008 * (idx + 1), 5), round(lat + 0.004 * ((idx % 4) - 1), 5)]}, "properties": {"entity_type": "Well", "rig_id": rig_id, "canonical_iri": f"cepio://well/{well_id}"}})
    features.append({"type": "Feature", "id": "move-rig-07", "geometry": {"type": "LineString", "coordinates": [[50.04, 26.50], [50.07, 26.53], [50.10, 26.55]]}, "properties": {"entity_type": "JackUpMove", "rig_id": "rig-07", "synthetic": True}})
    payload = {"type": "FeatureCollection", "name": "cepio-drilling-v0.2-geospatial", "features": features}
    path = Path("geospatial/rig-well-context.geojson")
    _write_text(output / path, json.dumps(payload, indent=2) + "\n")
    spec = SCENARIOS["SCN-001"]
    return [_artifact("SCN-001", "geospatial", path, "application/geo+json", spec, START, ["rig_location", "well_location", "rig_move_path"])]


def _write_waveforms(output: Path, samples: int, seed: int) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    sample_rate_hz = 2048.0
    for scenario_id, spec in SCENARIOS.items():
        rng = random.Random(seed + int(scenario_id[-1]) * 100)
        rows: list[dict[str, object]] = []
        base_f = float(spec["base_frequency_hz"])
        fault_f = float(spec["fault_frequency_hz"])
        for index in range(samples):
            t = index / sample_rate_hz
            base = math.sin(2 * math.pi * base_f * t)
            fault = 0.42 * math.sin(2 * math.pi * fault_f * t)
            modulation = 0.12 * math.sin(2 * math.pi * 7.0 * t)
            noise = rng.gauss(0.0, 0.04)
            if scenario_id == "SCN-003":
                value = 5000.0 - (index / max(samples - 1, 1)) * 260.0 + 18.0 * fault + noise * 10
            elif scenario_id == "SCN-004":
                value = 3100.0 + 180.0 * base + 95.0 * fault + noise * 30
            elif scenario_id == "SCN-002":
                value = 420.0 + 22.0 * base + 13.0 * fault + noise * 8
            else:
                value = 3.2 + 2.4 * base + 1.6 * fault + modulation + noise
            rows.append({"sample_index": index, "elapsed_ms": round(t * 1000, 6), "value": round(value, 6), "unit": spec["unit"]})
        path = Path("signals/high-frequency") / f"{scenario_id.lower()}-{spec['signal']}.csv"
        _write_csv(output / path, rows)
        artifacts.append(_artifact(scenario_id, "high_frequency_signal", path, "text/csv", spec, START + timedelta(days=float(spec["event_day"])), ["waveform_signature", "fault_frequency_component"]))
    return artifacts


def _write_visuals(output: Path) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    for scenario_id, spec in SCENARIOS.items():
        event_time = START + timedelta(days=float(spec["event_day"]))
        image_path = Path("images/inspection") / f"{scenario_id.lower()}-{spec['image_feature']}.ppm"
        diagram_path = Path("engineering/diagrams") / f"{scenario_id.lower()}-context.svg"
        _write_ppm(output / image_path, scenario_id)
        _write_svg(output / diagram_path, scenario_id, str(spec["diagram_component"]), str(spec["canonical_iri"]))
        artifacts.append(_artifact(scenario_id, "inspection_image", image_path, "image/x-portable-pixmap", spec, event_time - timedelta(hours=1), [str(spec["image_feature"]), "asset_identity"]))
        artifacts.append(_artifact(scenario_id, "engineering_diagram", diagram_path, "image/svg+xml", spec, event_time, ["asset_component_relationship", str(spec["diagram_component"])]))
    return artifacts


def generate_multimodal_dataset(output: Path, telemetry_points: int = 12000, waveform_samples: int = 4096, seed: int = DEFAULT_SEED) -> dict[str, object]:
    output = Path(output)
    v01 = _load_v01()
    base_manifest = v01.generate_dataset(output, telemetry_points=telemetry_points, seed=seed)

    artifacts: list[dict[str, object]] = []
    artifacts.extend(_write_documents(output))
    artifacts.extend(_write_visuals(output))
    artifacts.extend(_write_geojson(output))
    artifacts.extend(_write_waveforms(output, waveform_samples, seed))

    modality_counts: dict[str, int] = {}
    for artifact in artifacts:
        modality = str(artifact["modality"])
        modality_counts[modality] = modality_counts.get(modality, 0) + 1

    artifact_index = {"dataset": "cepio-synthetic-drilling", "version": DATASET_VERSION, "artifacts": artifacts}
    _write_text(output / "multimodal/artifact-index.json", json.dumps(artifact_index, indent=2) + "\n")

    manifest: dict[str, object] = dict(base_manifest)
    manifest["version"] = DATASET_VERSION
    manifest["inherits"] = "drilling-v0.1"
    manifest["multimodal"] = {
        "artifact_index": "multimodal/artifact-index.json",
        "modalities": modality_counts,
        "waveform_samples_per_scenario": waveform_samples,
        "principle": "source artifacts are bound to canonical CEPIO objects; raw artifact payloads remain source-native",
    }
    _write_text(output / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CEPIO Synthetic Industrial Dataset — Drilling v0.2 multimodal")
    parser.add_argument("--output", type=Path, default=Path(".generated/drilling-v0.2"))
    parser.add_argument("--telemetry-points", type=int, default=12000)
    parser.add_argument("--waveform-samples", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    print(json.dumps(generate_multimodal_dataset(args.output, args.telemetry_points, args.waveform_samples, args.seed), indent=2))


if __name__ == "__main__":
    main()
