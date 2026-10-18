from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from scripts.build_drilling_domain_qualification_v041 import normalize as normalize_v041

COMMERCIAL = "https://cepio.org/ontology/commercial#"
DRILL = "https://cepio.org/ontology/drilling#"


def normalize(source: dict) -> dict:
    data = normalize_v041(source)
    data["id"] = "drilling-contractor-domain-qualification-v0.4.2"
    data["version"] = "0.4.2"

    question = next(item for item in data["questions"] if item["id"] == "DC-DQ-003")
    alternative = question["capabilities"][0]["alternatives"][0]
    alternative["terms"].append({"iri": f"{COMMERCIAL}CostRecord", "kind": "class"})
    alternative["edges"] = [
        {
            "source": f"{COMMERCIAL}ContractRate",
            "predicate": f"{COMMERCIAL}rateForContract",
            "target": f"{DRILL}DrillingContract",
        },
        {
            "source": f"{COMMERCIAL}RevenueRecord",
            "predicate": f"{COMMERCIAL}revenueFor",
            "target": f"{DRILL}DrillingContract",
        },
        {
            "source": f"{COMMERCIAL}CostRecord",
            "predicate": f"{COMMERCIAL}costFor",
            "target": f"{DRILL}DrillingContract",
        },
    ]
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="generalization/competency/drilling-contractor-domain-qualification-v0.4.yaml",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = yaml.safe_load(Path(args.source).read_text())
    normalized = normalize(source)
    Path(args.out).write_text(yaml.safe_dump(normalized, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
