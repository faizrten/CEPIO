from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "generalization/competency/refinery-process-manufacturing-v0.1.yaml"
BUILDER = ROOT / "scripts/build_refinery_normalized_benchmark.py"


def test_normalization_preserves_business_exam_and_only_corrects_patterns(tmp_path: Path) -> None:
    out = tmp_path / "refinery-process-manufacturing-v0.1.2.yaml"
    subprocess.run(
        [sys.executable, str(BUILDER), "--source", str(RAW), "--out", str(out)],
        cwd=ROOT,
        check=True,
    )

    raw = yaml.safe_load(RAW.read_text(encoding="utf-8"))
    normalized = yaml.safe_load(out.read_text(encoding="utf-8"))

    assert raw["id"] == "refinery-process-manufacturing-capabilities-v0.1"
    assert normalized["id"] == "refinery-process-manufacturing-capabilities-v0.1.2"
    assert normalized["version"] == "0.1.2"
    assert normalized["normalized_from"] == raw["id"]
    assert len(raw["questions"]) == len(normalized["questions"]) == 16

    for raw_question, normalized_question in zip(raw["questions"], normalized["questions"], strict=True):
        assert raw_question["id"] == normalized_question["id"]
        assert raw_question["question"] == normalized_question["question"]
        assert raw_question["priority"] == normalized_question["priority"]
        assert raw_question["personas"] == normalized_question["personas"]
        assert raw_question["standards"] == normalized_question["standards"]
        assert [item["id"] for item in raw_question["capabilities"]] == [
            item["id"] for item in normalized_question["capabilities"]
        ]

    rendered = out.read_text(encoding="utf-8")
    assert "https://cepio.org/ontology/process#ProcessUnit" not in rendered
    assert "https://cepio.org/ontology/process#streamFeedsUnit" not in rendered
    assert "https://cepio.org/ontology/process#ProcessTrip" not in rendered
    assert "https://cepio.org/ontology/manufacturing#Specification" not in rendered
    assert "https://cepio.org/ontology/manufacturing#lotConformsToSpecification" not in rendered
    assert "https://cepio.org/ontology/performance#EnergyIntensityKPI" not in rendered

    assert "https://cepio.org/ontology/industrial#ProcessUnit" in rendered
    assert "https://cepio.org/ontology/process#streamToUnit" in rendered
    assert "https://cepio.org/ontology/manufacturing#MaterialSpecification" in rendered
    assert "https://cepio.org/ontology/manufacturing#lotEvaluatedAgainstSpecification" in rendered
    assert "https://cepio.org/ontology/manufacturing#dispositionForLot" in rendered
    assert "https://cepio.org/ontology/process#emissionFromUnit" in rendered
    assert "https://cepio.org/ontology/process#meterAtUnit" in rendered
    assert "https://cepio.org/ontology/core#KPI" in rendered
    assert "https://cepio.org/ontology/industrial#TripEvent" in rendered
    assert "https://cepio.org/ontology/hse#eventAtAsset" in rendered


def test_historical_v011_normalization_record_remains_immutable() -> None:
    record = yaml.safe_load(
        (ROOT / "generalization/normalization/refinery-process-manufacturing-v0.1.1.yaml").read_text(encoding="utf-8")
    )
    assert record["policy"]["preserve_raw_baseline"] is True
    assert record["policy"]["business_questions_immutable"] is True
    assert record["policy"]["ontology_changes_allowed"] is False
    assert len(record["corrections"]) == 5


def test_v012_normalization_record_preserves_exam_and_records_new_corrections() -> None:
    record = yaml.safe_load(
        (ROOT / "generalization/normalization/refinery-process-manufacturing-v0.1.2.yaml").read_text(encoding="utf-8")
    )
    assert record["policy"]["preserve_raw_baseline"] is True
    assert record["policy"]["business_questions_immutable"] is True
    correction_ids = {item["id"] for item in record["corrections"]}
    assert {
        "lot-material-specification",
        "quality-disposition-lot",
        "energy-intensity-kpi-identity",
    }.issubset(correction_ids)
