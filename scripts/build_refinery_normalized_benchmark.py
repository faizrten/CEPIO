from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

PROCESS_UNIT = "https://cepio.org/ontology/process#ProcessUnit"
IND_PROCESS_UNIT = "https://cepio.org/ontology/industrial#ProcessUnit"
PROCESS_TRIP = "https://cepio.org/ontology/process#ProcessTrip"
IND_TRIP_EVENT = "https://cepio.org/ontology/industrial#TripEvent"


def _replace_scalar(node: Any, old: str, new: str) -> Any:
    if isinstance(node, dict):
        return {key: _replace_scalar(value, old, new) for key, value in node.items()}
    if isinstance(node, list):
        return [_replace_scalar(value, old, new) for value in node]
    if node == old:
        return new
    return node


def _question(pack: dict[str, Any], question_id: str) -> dict[str, Any]:
    for question in pack["questions"]:
        if question["id"] == question_id:
            return question
    raise KeyError(f"question not found: {question_id}")


def _capability(question: dict[str, Any], capability_id: str) -> dict[str, Any]:
    for capability in question["capabilities"]:
        if capability["id"] == capability_id:
            return capability
    raise KeyError(f"capability not found: {question['id']} / {capability_id}")


def _single_alternative(pack: dict[str, Any], question_id: str, capability_id: str) -> dict[str, Any]:
    capability = _capability(_question(pack, question_id), capability_id)
    alternatives = capability["alternatives"]
    if len(alternatives) != 1:
        raise ValueError(f"expected exactly one alternative for {question_id}/{capability_id}")
    return alternatives[0]


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    pack = deepcopy(raw)
    if pack.get("id") != "refinery-process-manufacturing-capabilities-v0.1":
        raise ValueError("unexpected source competency pack id")
    if pack.get("version") != "0.1":
        raise ValueError("unexpected source competency pack version")
    if len(pack.get("questions", [])) != 16:
        raise ValueError("expected the frozen 16-question refinery pack")

    # Canonical identity correction: CEPIO already defines ProcessUnit in industrial.ttl.
    pack = _replace_scalar(pack, PROCESS_UNIT, IND_PROCESS_UNIT)

    # RP-PC-001: use the existing stream topology instead of a nonexistent streamFeedsUnit edge.
    alt = _single_alternative(pack, "RP-PC-001", "process-unit-flow-context")
    expected = [{
        "source": "https://cepio.org/ontology/process#MaterialStream",
        "predicate": "https://cepio.org/ontology/process#streamFeedsUnit",
        "target": IND_PROCESS_UNIT,
    }]
    if alt.get("edges") != expected:
        raise ValueError("RP-PC-001 source pattern changed; normalization must be reviewed")
    alt["edges"] = [{
        "source": "https://cepio.org/ontology/process#MaterialStream",
        "predicate": "https://cepio.org/ontology/process#streamToUnit",
        "target": IND_PROCESS_UNIT,
    }]

    # RP-PC-009: preserve the emission-limit requirement but correct the unit-context direction.
    alt = _single_alternative(pack, "RP-PC-009", "emissions-evidence")
    old_edge = {
        "source": IND_PROCESS_UNIT,
        "predicate": "https://cepio.org/ontology/core#measuredBy",
        "target": "https://cepio.org/ontology/process#EmissionObservation",
    }
    new_edge = {
        "source": "https://cepio.org/ontology/process#EmissionObservation",
        "predicate": "https://cepio.org/ontology/process#emissionFromUnit",
        "target": IND_PROCESS_UNIT,
    }
    edges = alt.get("edges", [])
    if old_edge not in edges:
        raise ValueError("RP-PC-009 source pattern changed; normalization must be reviewed")
    alt["edges"] = [new_edge if edge == old_edge else edge for edge in edges]

    # RP-PC-010: UtilityMeter is Equipment, not Measurement. Scope stream and meter to the same unit.
    alt = _single_alternative(pack, "RP-PC-010", "utility-metering")
    expected = [{
        "source": "https://cepio.org/ontology/process#UtilityStream",
        "predicate": "https://cepio.org/ontology/core#measuredBy",
        "target": "https://cepio.org/ontology/process#UtilityMeter",
    }]
    if alt.get("edges") != expected:
        raise ValueError("RP-PC-010 source pattern changed; normalization must be reviewed")
    alt["edges"] = [
        {
            "source": "https://cepio.org/ontology/process#UtilityStream",
            "predicate": "https://cepio.org/ontology/process#streamToUnit",
            "target": IND_PROCESS_UNIT,
        },
        {
            "source": "https://cepio.org/ontology/process#UtilityMeter",
            "predicate": "https://cepio.org/ontology/process#meterAtUnit",
            "target": IND_PROCESS_UNIT,
        },
    ]

    # RP-PC-013: reuse CEPIO's generic industrial trip event rather than inventing ProcessTrip.
    question = _question(pack, "RP-PC-013")
    question = _replace_scalar(question, PROCESS_TRIP, IND_TRIP_EVENT)
    for index, candidate in enumerate(pack["questions"]):
        if candidate["id"] == "RP-PC-013":
            pack["questions"][index] = question
            break
    alt = _single_alternative(pack, "RP-PC-013", "process-trip")
    expected = [{
        "source": IND_TRIP_EVENT,
        "predicate": "https://cepio.org/ontology/process#tripOfUnit",
        "target": IND_PROCESS_UNIT,
    }]
    if alt.get("edges") != expected:
        raise ValueError("RP-PC-013 source pattern changed; normalization must be reviewed")
    alt["edges"] = [{
        "source": IND_TRIP_EVENT,
        "predicate": "https://cepio.org/ontology/hse#eventAtAsset",
        "target": IND_PROCESS_UNIT,
    }]

    pack["id"] = "refinery-process-manufacturing-capabilities-v0.1.1"
    pack["version"] = "0.1.1"
    pack["normalized_from"] = "refinery-process-manufacturing-capabilities-v0.1"
    pack["normalization_record"] = "generalization/normalization/refinery-process-manufacturing-v0.1.1.yaml"
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the normalized refinery benchmark without modifying ontology semantics.")
    parser.add_argument(
        "--source",
        default="generalization/competency/refinery-process-manufacturing-v0.1.yaml",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    out = Path(args.out)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    normalized = normalize(raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(normalized, sort_keys=False), encoding="utf-8")
    print(f"wrote normalized refinery benchmark: {out}")


if __name__ == "__main__":
    main()
