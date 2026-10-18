import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPETENCY = ROOT / "generalization/competency/drilling-contractor-domain-qualification-v0.4.yaml"
COMMERCIAL = "https://cepio.org/ontology/commercial#"
DRILL = "https://cepio.org/ontology/drilling#"


def test_v042_adds_cost_linked_economics_without_changing_frozen_v04(tmp_path):
    source = yaml.safe_load(COMPETENCY.read_text())
    output = tmp_path / "drilling-contractor-domain-qualification-v0.4.2.yaml"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_drilling_domain_qualification_v042.py"),
            "--source",
            str(COMPETENCY),
            "--out",
            str(output),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        check=True,
    )
    normalized = yaml.safe_load(output.read_text())

    assert source["version"] == "0.4"
    assert source["frozen"] is True
    assert normalized["id"] == "drilling-contractor-domain-qualification-v0.4.2"
    assert normalized["version"] == "0.4.2"

    question = next(item for item in normalized["questions"] if item["id"] == "DC-DQ-003")
    alternative = question["capabilities"][0]["alternatives"][0]
    assert {"iri": f"{COMMERCIAL}CostRecord", "kind": "class"} in alternative["terms"]
    assert {
        "source": f"{COMMERCIAL}RevenueRecord",
        "predicate": f"{COMMERCIAL}revenueFor",
        "target": f"{DRILL}DrillingContract",
    } in alternative["edges"]
    assert {
        "source": f"{COMMERCIAL}CostRecord",
        "predicate": f"{COMMERCIAL}costFor",
        "target": f"{DRILL}DrillingContract",
    } in alternative["edges"]
