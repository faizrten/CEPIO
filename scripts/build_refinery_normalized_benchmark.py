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
MFG_MATERIAL_LOT = "https://cepio.org/ontology/manufacturing#MaterialLot"
MFG_GENERIC_SPEC = "https://cepio.org/ontology/manufacturing#Specification"
MFG_MATERIAL_SPEC = "https://cepio.org/ontology/manufacturing#MaterialSpecification"
MFG_LOT_CONFORMS = "https://cepio.org/ontology/manufacturing#lotConformsToSpecification"
MFG_LOT_EVALUATED = "https://cepio.org/ontology/manufacturing#lotEvaluatedAgainstSpecification"
MFG_QUALITY_DISPOSITION = "https://cepio.org/ontology/manufacturing#QualityDisposition"
MFG_DISPOSITION_FOR_LOT = "https://cepio.org/ontology/manufacturing#dispositionForLot"
PERF_ENERGY_INTENSITY_KPI = "https://cepio.org/ontology/performance#EnergyIntensityKPI"
CORE_KPI = "https://cepio.org/ontology/core#KPI"
CORE_MEASURED_BY = "https://cepio.org/ontology/core#measuredBy"
CORE_IMPACTS = "https://cepio.org/ontology/core#impacts"


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

    # RP-PC-008: reuse canonical MaterialSpecification and separate lot evaluation
    # from the actual pass/fail result. An off-spec lot cannot truthfully be linked
    # by a predicate named lotConformsToSpecification.
    alt = _single_alternative(pack, "RP-PC-008", "lot-specification")
    expected_terms = [
        {"iri": MFG_MATERIAL_LOT, "kind": "class"},
        {"iri": MFG_GENERIC_SPEC, "kind": "class"},
    ]
    expected_edges = [{
        "source": MFG_MATERIAL_LOT,
        "predicate": MFG_LOT_CONFORMS,
        "target": MFG_GENERIC_SPEC,
    }]
    if alt.get("terms") != expected_terms or alt.get("edges") != expected_edges:
        raise ValueError("RP-PC-008 lot-specification source pattern changed; normalization must be reviewed")
    alt["terms"] = [
        {"iri": MFG_MATERIAL_LOT, "kind": "class"},
        {"iri": MFG_MATERIAL_SPEC, "kind": "class"},
    ]
    alt["edges"] = [{
        "source": MFG_MATERIAL_LOT,
        "predicate": MFG_LOT_EVALUATED,
        "target": MFG_MATERIAL_SPEC,
    }]

    # RP-PC-008: use an explicit disposition-to-lot relationship rather than the
    # very broad core impacts predicate. The class remains manufacturing-common.
    alt = _single_alternative(pack, "RP-PC-008", "quality-disposition")
    expected_edges = [{
        "source": MFG_QUALITY_DISPOSITION,
        "predicate": CORE_IMPACTS,
        "target": MFG_MATERIAL_LOT,
    }]
    if alt.get("edges") != expected_edges:
        raise ValueError("RP-PC-008 quality-disposition source pattern changed; normalization must be reviewed")
    alt["edges"] = [{
        "source": MFG_QUALITY_DISPOSITION,
        "predicate": MFG_DISPOSITION_FOR_LOT,
        "target": MFG_MATERIAL_LOT,
    }]

    # RP-PC-009: preserve the emission-limit requirement but correct the unit-context direction.
    alt = _single_alternative(pack, "RP-PC-009", "emissions-evidence")
    old_edge = {
        "source": IND_PROCESS_UNIT,
        "predicate": CORE_MEASURED_BY,
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
        "predicate": CORE_MEASURED_BY,
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

    # RP-PC-010: Energy intensity is a KPI identity/formula, not an ontology
    # class. Reuse the canonical KPI contract; ISO 50001 identity, formula,
    # denominator, units, baseline and target live in performance_kpis mappings.
    alt = _single_alternative(pack, "RP-PC-010", "energy-intensity")
    expected_terms = [{"iri": PERF_ENERGY_INTENSITY_KPI, "kind": "class"}]
    expected_edges = [{
        "source": IND_PROCESS_UNIT,
        "predicate": CORE_MEASURED_BY,
        "target": PERF_ENERGY_INTENSITY_KPI,
    }]
    if alt.get("terms") != expected_terms or alt.get("edges") != expected_edges:
        raise ValueError("RP-PC-010 energy-intensity source pattern changed; normalization must be reviewed")
    alt["terms"] = [{"iri": CORE_KPI, "kind": "class"}]
    alt["edges"] = [{
        "source": IND_PROCESS_UNIT,
        "predicate": CORE_MEASURED_BY,
        "target": CORE_KPI,
    }]

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

    pack["id"] = "refinery-process-manufacturing-capabilities-v0.1.2"
    pack["version"] = "0.1.2"
    pack["normalized_from"] = "refinery-process-manufacturing-capabilities-v0.1"
    pack["normalization_record"] = "generalization/normalization/refinery-process-manufacturing-v0.1.2.yaml"
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the normalized refinery benchmark without weakening genuine competency requirements.")
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
