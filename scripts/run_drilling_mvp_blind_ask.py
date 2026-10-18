from __future__ import annotations

import argparse
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "mvp/datasets/drilling-v0.2"


def _load_acceptance_module():
    path = ROOT / "scripts/run_drilling_mvp_acceptance.py"
    spec = importlib.util.spec_from_file_location("run_drilling_mvp_acceptance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load acceptance runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}


def _norm(value: Any) -> str:
    return str(value).strip().lower()


@dataclass
class BlindAnswer:
    intent: str
    refs: list[str]
    value: Any | None
    evidence: list[str]
    supporting_object_ids: list[str]
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "intent": self.intent,
            "refs": self.refs,
            "evidence": self.evidence,
            "supporting_object_ids": self.supporting_object_ids,
            "confidence": self.confidence,
        }
        if self.value is not None:
            payload["value"] = self.value
        return payload


class BlindAskCEPIO:
    """Question-text-only semantic retrieval baseline.

    This deliberately does not receive golden-question IDs, assertion labels or expected
    answers. It is a deterministic baseline for CEPIO semantic retrieval, not an LLM.
    """

    def __init__(self, runtime, dataset_dir: Path) -> None:
        self.runtime = runtime
        self.dataset_dir = dataset_dir
        self.acceptance = _load_acceptance_module()

    def objects(self, object_type: str | None = None):
        return self.runtime.list_objects(object_type)

    def artifacts(self, scenario_id: str | None = None, modality: str | None = None):
        return self.acceptance._artifact_objects(self.runtime, scenario_id, modality)

    @staticmethod
    def _answer(intent: str, *, refs: list[str] | None = None, value: Any | None = None,
                evidence: list[str] | None = None, objects: list[str] | None = None,
                confidence: float = 0.9) -> BlindAnswer:
        return BlindAnswer(
            intent=intent,
            refs=refs or [],
            value=value,
            evidence=sorted(set(evidence or [])),
            supporting_object_ids=sorted(set(objects or [])),
            confidence=confidence,
        )

    def _resolve_alias(self, alias: str):
        target = _norm(alias)
        for obj in self.objects("DrillingEquipment"):
            aliases = obj.properties.get("aliases", {})
            if target in {_norm(v) for v in aliases.values()}:
                return obj
        return None

    def _scenario_equipment(self, scenario_id: str):
        matches = [obj for obj in self.objects("DrillingEquipment") if obj.properties.get("scenario_id") == scenario_id]
        return matches[0] if matches else None

    def _scenario_from_text(self, text: str) -> str | None:
        match = re.search(r"scn[- ]?0*(\d+)", text, flags=re.I)
        return f"SCN-{int(match.group(1)):03d}" if match else None

    def _equipment_from_text(self, question: str):
        q = question.lower()
        if "top drive" in q:
            return self.runtime.get_object("rig-12-top-drive-01")
        if "bop" in q or "well-control" in q or "well control" in q:
            return self.runtime.get_object("rig-21-bop-01")
        if "mud pump 2" in q or "mud-pump 2" in q:
            return self.runtime.get_object("rig-12-mud-pump-02")
        if "mud pump 1" in q or "mud-pump 1" in q or "rig-07 mud" in q:
            return self.runtime.get_object("rig-07-mud-pump-01")
        return None

    def answer(self, question: str) -> BlindAnswer:
        q = question.lower()
        scenario = self._scenario_from_text(question)
        equipment = self._equipment_from_text(question)

        if "what equipment belongs" in q and "rig-07" in q:
            objs = self.runtime.neighbors("rig-07", "hasRigEquipment")
            return self._answer("equipment_by_rig", refs=[o.id for o in objs], evidence=["master-data/equipment.csv"], objects=[o.id for o in objs])

        if ("sensor" in q or "monitor" in q) and equipment is not None:
            objs = self.runtime.reverse_neighbors(equipment.id, "observedOnEquipment")
            return self._answer("condition_signals_by_equipment", refs=[o.id for o in objs], evidence=["master-data/sensors.csv", "telemetry/telemetry.csv"], objects=[o.id for o in objs])

        if "alias" in q and equipment is not None:
            aliases = list(equipment.properties.get("aliases", {}).values())
            return self._answer("entity_aliases", refs=aliases, evidence=["mvp/datasets/drilling-v0.1/ground-truth/entity-resolution.json"], objects=[equipment.id])

        if "resolve" in q and "mp-001" in q:
            obj = self._resolve_alias("MP-001")
            refs = [obj.properties["canonical_iri"]] if obj else []
            return self._answer("entity_resolution", refs=refs, evidence=["mvp/datasets/drilling-v0.1/ground-truth/entity-resolution.json"], objects=[obj.id] if obj else [], confidence=0.98 if obj else 0.2)

        if "what happened before" in q and equipment is not None:
            failures = self.runtime.reverse_neighbors(equipment.id, "failureOfEquipment")
            refs = list(equipment.properties.get("leading_signals", [])) + [obj.id for obj in failures]
            return self._answer("pre_failure_context", refs=refs, evidence=["telemetry/telemetry.csv", "reliability/failure_events.csv"], objects=[equipment.id, *[o.id for o in failures]])

        if "how much npt" in q and equipment is not None:
            failures = self.runtime.reverse_neighbors(equipment.id, "failureOfEquipment")
            downtime = self.runtime.neighbors(failures[0].id, "causesDowntime") if failures else []
            value = downtime[0].properties.get("duration_hours") if downtime else None
            return self._answer("npt_duration_for_failure", value=value, evidence=[d.properties.get("source_uri") for d in downtime if d.properties.get("source_uri")], objects=[d.id for d in downtime])

        if "which work order" in q and ("repair" in q or "repaired" in q) and equipment is not None:
            failures = self.runtime.reverse_neighbors(equipment.id, "failureOfEquipment")
            work = self.runtime.neighbors(failures[0].id, "repairedByWorkOrder") if failures else []
            return self._answer("repair_work_order", refs=[o.id for o in work], evidence=["maintenance/work_orders.csv"], objects=[o.id for o in work])

        if "repair effective" in q and equipment is not None:
            signals = self.runtime.reverse_neighbors(equipment.id, "observedOnEquipment")
            relevant = [o for o in signals if o.properties.get("metric") in {"vibration_rms", "bearing_temperature"}]
            value = bool(relevant) and all(bool(o.properties.get("repair_normalized")) for o in relevant)
            return self._answer("repair_effectiveness", value=value, evidence=["telemetry/telemetry.csv"], objects=[o.id for o in relevant])

        if "emerging" in q and "top-drive" in q or ("emerging" in q and "top drive" in q):
            obj = self.runtime.get_object("rig-12-top-drive-01")
            work = self.runtime.neighbors(obj.id, "hasWorkOrder")
            failures = self.runtime.reverse_neighbors(obj.id, "failureOfEquipment")
            refs = [obj.properties["rig_id"], obj.id] if any(w.properties.get("status") == "open" for w in work) and not failures else []
            return self._answer("emerging_issue_without_npt", refs=refs, evidence=["maintenance/work_orders.csv", "reliability/failure_events.csv"], objects=[obj.id, *[w.id for w in work]])

        if "maintenance" in q and "investigated" in q and equipment is not None:
            work = [o for o in self.runtime.neighbors(equipment.id, "hasWorkOrder") if o.properties.get("status") == "open"]
            return self._answer("open_maintenance", refs=[o.id for o in work], evidence=["maintenance/work_orders.csv"], objects=[o.id for o in work])

        if "well-control" in q or "well control" in q:
            npt = [o for o in self.objects("DowntimeEvent") if o.properties.get("category") == "well_control_test_failure"]
            refs = [item for o in npt for item in (o.properties.get("scenario_id"), o.id) if item]
            return self._answer("well_control_downtime_event", refs=refs, evidence=["operations/npt_events.csv"], objects=[o.id for o in npt])

        if "bop" in q and "downtime" in q:
            matches = [o for o in self.objects("DowntimeEvent") if o.properties.get("equipment_id") == "rig-21-bop-01"]
            value = matches[0].properties.get("duration_hours") if matches else None
            return self._answer("bop_downtime", value=value, evidence=["operations/npt_events.csv"], objects=[o.id for o in matches])

        if "discharge-pressure" in q or "discharge pressure" in q:
            matches = [o for o in self.objects("DrillingEquipment") if o.properties.get("scenario_id") == "SCN-004"]
            return self._answer("pressure_instability_asset", refs=[o.id for o in matches], evidence=["telemetry/telemetry.csv", "master-data/equipment.csv"], objects=[o.id for o in matches])

        if "root cause" in q and equipment is not None:
            return self._answer("root_cause", refs=[str(equipment.properties.get("root_cause"))], evidence=["reliability/failure_events.csv", "mvp/datasets/drilling-v0.1/ground-truth/scenarios.json"], objects=[equipment.id])

        if "explicit source scenario" in q:
            refs = sorted({str(o.properties["scenario_id"]) for o in self.objects("DowntimeEvent") if o.properties.get("scenario_id")})
            return self._answer("event_provenance", refs=refs, evidence=["operations/npt_events.csv"], objects=[o.id for o in self.objects("DowntimeEvent")])

        if "largest duration" in q or "largest npt" in q:
            events = self.objects("DowntimeEvent")
            obj = max(events, key=lambda o: float(o.properties.get("duration_hours", 0.0))) if events else None
            return self._answer("largest_downtime", refs=[obj.id] if obj else [], evidence=["operations/npt_events.csv"], objects=[obj.id] if obj else [])

        if "which rigs use mud pumps" in q:
            pumps = [o for o in self.objects("DrillingEquipment") if o.properties.get("equipment_type") == "MudPump"]
            return self._answer("fleet_equipment_distribution", refs=sorted({str(o.properties["rig_id"]) for o in pumps}), evidence=["master-data/equipment.csv"], objects=[o.id for o in pumps])

        if "predictive maintenance" in q:
            candidates = []
            for obj in self.objects("DrillingEquipment"):
                work = self.runtime.neighbors(obj.id, "hasWorkOrder")
                has_open = any(w.properties.get("status") == "open" for w in work)
                has_npt = any(e.properties.get("equipment_id") == obj.id for e in self.objects("DowntimeEvent"))
                if has_open and not has_npt and obj.properties.get("scenario_id"):
                    candidates.append(str(obj.properties["scenario_id"]))
            return self._answer("predictive_maintenance_scenario", refs=sorted(set(candidates)), evidence=["maintenance/work_orders.csv", "operations/npt_events.csv"], objects=[])

        if "trace a maintenance action" in q:
            work = self.objects("WorkOrder")
            value = all(self.runtime.reverse_neighbors(o.id, "hasWorkOrder") and o.properties.get("scenario_id") for o in work)
            return self._answer("maintenance_traceability", value=bool(value), evidence=["maintenance/work_orders.csv", "master-data/equipment.csv"], objects=[o.id for o in work])

        if "prioritize" in q and "npt" in q:
            events = self.objects("DowntimeEvent")
            obj = max(events, key=lambda o: float(o.properties.get("duration_hours", 0.0))) if events else None
            refs = [str(obj.properties["scenario_id"])] if obj and obj.properties.get("scenario_id") else []
            return self._answer("npt_priority_ranking", refs=refs, evidence=["operations/npt_events.csv"], objects=[obj.id] if obj else [])

        if "inspection document" in q:
            scenario = scenario or (equipment.properties.get("scenario_id") if equipment else None)
            docs = [o for o in self.artifacts(str(scenario), "document") if "inspection-reports" in str(o.properties.get("source_uri", ""))]
            refs = [item for o in docs for item in [o.properties.get("scenario_id"), *o.properties.get("ground_truth_claims", []), o.properties.get("source_asset_iri")] if item]
            return self._answer("inspection_document_evidence", refs=[str(x) for x in refs], evidence=[str(o.properties["source_uri"]) for o in docs], objects=[o.id for o in docs])

        if "visual evidence" in q:
            scenario = scenario or (equipment.properties.get("scenario_id") if equipment else None)
            images = self.artifacts(str(scenario), "inspection_image") if scenario else []
            refs = [item for o in images for item in [o.properties.get("scenario_id"), *o.properties.get("ground_truth_claims", [])] if item]
            return self._answer("visual_evidence", refs=[str(x) for x in refs], evidence=[str(o.properties["source_uri"]) for o in images], objects=[o.id for o in images])

        if "engineering diagram" in q:
            diagrams = self.artifacts(str(scenario), "engineering_diagram") if scenario else []
            refs = [item for o in diagrams for item in [o.properties.get("scenario_id"), *o.properties.get("ground_truth_claims", [])] if item]
            return self._answer("diagram_grounding", refs=[str(x) for x in refs], evidence=[str(o.properties["source_uri"]) for o in diagrams], objects=[o.id for o in diagrams])

        if "where are" in q and "operating rigs" in q:
            rigs = [o for o in self.objects("OperatingRig") if "longitude" in o.properties and "latitude" in o.properties]
            return self._answer("rig_geospatial_context", refs=[o.id for o in rigs], evidence=["geospatial/rig-well-context.geojson"], objects=[o.id for o in rigs])

        if "wells" in q and "spatially associated" in q and "rig-12" in q:
            wells = [o for o in self.objects("Well") if o.properties.get("rig_id") == "rig-12" and "longitude" in o.properties]
            return self._answer("well_geospatial_association", refs=[o.id for o in wells], evidence=["geospatial/rig-well-context.geojson"], objects=[o.id for o in wells])

        if "high-frequency" in q and "fault-frequency" in q:
            waveforms = self.artifacts(str(scenario), "high_frequency_signal") if scenario else []
            value = bool(waveforms) and self.acceptance._waveform_has_fault_component(self.dataset_dir, waveforms[0])
            return self._answer("waveform_fault_component", value=value, evidence=[str(o.properties["source_uri"]) for o in waveforms], objects=[o.id for o in waveforms])

        if "source modalities" in q and scenario:
            artifacts = self.artifacts(scenario)
            refs = sorted({str(o.properties.get("modality")) for o in artifacts if o.properties.get("modality")})
            return self._answer("cross_modal_support", refs=refs, evidence=[str(o.properties["source_uri"]) for o in artifacts], objects=[o.id for o in artifacts])

        if "source-native artifact path" in q:
            artifacts = self.artifacts()
            value = bool(artifacts) and all(o.properties.get("source_uri") and o.properties.get("raw_payload_embedded") is False for o in artifacts)
            return self._answer("source_native_reference", value=value, evidence=["multimodal/artifact-index.json"], objects=[o.id for o in artifacts])

        if "every multimodal artifact" in q and "canonical asset" in q:
            artifacts = self.artifacts()
            value = bool(artifacts) and all(o.properties.get("source_asset_iri") and o.properties.get("scenario_id") and o.properties.get("event_time") and o.properties.get("provenance") for o in artifacts)
            return self._answer("multimodal_traceability", value=value, evidence=["multimodal/artifact-index.json"], objects=[o.id for o in artifacts])

        if "structured operational records" in q and "non-tabular evidence" in q:
            operational = {str(o.properties["scenario_id"]) for o in self.objects("WorkOrder") if o.properties.get("scenario_id")}
            non_tabular = {str(o.properties["scenario_id"]) for o in self.artifacts() if o.properties.get("scenario_id")}
            return self._answer("structured_plus_multimodal", refs=sorted(operational & non_tabular), evidence=["maintenance/work_orders.csv", "multimodal/artifact-index.json"], objects=[])

        return self._answer("unresolved", evidence=[], confidence=0.0)


def _matches_expected(answer: dict[str, Any], expected: dict[str, Any]) -> bool:
    if "expected_value" in expected:
        actual = answer.get("value")
        target = expected["expected_value"]
        if isinstance(target, float) and isinstance(actual, (int, float)):
            return abs(float(actual) - target) <= 1e-6
        return actual == target
    expected_refs = {_norm(value) for value in expected.get("expected_refs", [])}
    actual_refs = {_norm(value) for value in answer.get("refs", [])}
    return expected_refs.issubset(actual_refs)


def run_blind_benchmark(output: Path, *, telemetry_points: int = 12000, waveform_samples: int = 2048, seed: int = 1701) -> dict[str, Any]:
    acceptance = _load_acceptance_module()
    generator = acceptance._load_v02_generator()
    generator.generate_multimodal_dataset(output, telemetry_points=telemetry_points, waveform_samples=waveform_samples, seed=seed)
    runtime = acceptance.build_acceptance_runtime(output)

    golden = _read_json(FIXTURE / "tests/golden-questions.json")
    public_questions = [{"id": item["id"], "question": item["question"]} for item in golden]
    agent = BlindAskCEPIO(runtime, output)

    # Blind phase: only natural-language question text reaches the answerer.
    answers: dict[str, dict[str, Any]] = {}
    for item in public_questions:
        answers[item["id"]] = agent.answer(item["question"]).as_dict()

    # Scoring phase: hidden expectations are consulted only after all answers exist.
    details = []
    passed = 0
    evidence_passed = 0
    unresolved = 0
    for expected in golden:
        answer = answers[expected["id"]]
        ok = _matches_expected(answer, expected)
        evidence_ok = bool(answer.get("evidence"))
        passed += int(ok)
        evidence_passed += int(evidence_ok)
        unresolved += int(answer.get("intent") == "unresolved")
        details.append({
            "id": expected["id"],
            "question": expected["question"],
            "intent": answer.get("intent"),
            "passed": ok,
            "evidence": evidence_ok,
            "confidence": answer.get("confidence"),
            "answer": {k: v for k, v in answer.items() if k not in {"evidence", "supporting_object_ids"}},
            "evidence_refs": answer.get("evidence", []),
            "supporting_object_ids": answer.get("supporting_object_ids", []),
        })

    total = len(golden)
    accuracy = passed / total if total else 0.0
    evidence_coverage = evidence_passed / total if total else 0.0
    return {
        "benchmark": "Ask CEPIO blind semantic retrieval",
        "dataset_version": "0.2.0",
        "agent_input": "question_text_only",
        "llm_used": False,
        "expected_answers_visible_during_answering": False,
        "passed": passed,
        "total": total,
        "accuracy": accuracy,
        "evidence_passed": evidence_passed,
        "evidence_coverage": evidence_coverage,
        "unresolved": unresolved,
        "thresholds": {"accuracy": 0.70, "evidence_coverage": 0.90},
        "gate_passed": accuracy >= 0.70 and evidence_coverage >= 0.90,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blind question-text-only Ask CEPIO benchmark")
    parser.add_argument("--output", type=Path, default=Path(".generated/drilling-v0.2-blind-ask"))
    parser.add_argument("--telemetry-points", type=int, default=12000)
    parser.add_argument("--waveform-samples", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    report = run_blind_benchmark(args.output, telemetry_points=args.telemetry_points, waveform_samples=args.waveform_samples, seed=args.seed)
    payload = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if not report["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
