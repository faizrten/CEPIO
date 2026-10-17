from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_drilling_mvp_blind_ask",
    ROOT / "scripts/run_drilling_mvp_blind_ask.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_blind_ask_cepio_uses_question_text_only(tmp_path: Path):
    report = MODULE.run_blind_benchmark(
        tmp_path,
        telemetry_points=600,
        waveform_samples=512,
        seed=1701,
    )

    assert report["agent_input"] == "question_text_only"
    assert report["expected_answers_visible_during_answering"] is False
    assert report["total"] == 30
    assert report["accuracy"] >= 0.70, report
    assert report["evidence_coverage"] >= 0.90, report
    assert report["gate_passed"] is True, report
