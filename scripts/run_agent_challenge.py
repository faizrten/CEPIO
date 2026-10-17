from __future__ import annotations

import argparse
import importlib.util
import json
import math
import queue
import shlex
import statistics
import subprocess
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "mvp/benchmarks/agent-challenge-v0.1"
APPROVED_TOOLS = {
    "search_objects",
    "get_object",
    "get_relationships",
    "get_events",
    "resolve_identity",
    "get_evidence",
    "query_measurements",
    "get_provenance",
}


def _load_acceptance_module():
    path = ROOT / "scripts/run_drilling_mvp_acceptance.py"
    spec = importlib.util.spec_from_file_location("run_drilling_mvp_acceptance_agent_challenge", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load acceptance runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: Any) -> str:
    return str(value).strip().lower()


def _flatten(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            result.append(str(key))
            result.extend(_flatten(item))
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_flatten(item))
        return result
    return [str(value)]


def _object_view(obj) -> dict[str, Any]:
    properties = {
        key: value
        for key, value in obj.properties.items()
        if key not in {"source_uri", "geospatial_source_uri"}
    }
    return {
        "id": obj.id,
        "type": obj.type,
        "name": obj.name,
        "properties": properties,
    }


class CEPIOToolGateway:
    """Bounded semantic gateway for agent evaluation."""

    TOOL_SCHEMAS: list[dict[str, Any]] = [
        {
            "name": "search_objects",
            "description": "Search canonical CEPIO objects by text and optional CEPIO object type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "object_type": {"type": ["string", "null"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_object",
            "description": "Get one canonical CEPIO object by object ID.",
            "parameters": {
                "type": "object",
                "properties": {"object_id": {"type": "string"}},
                "required": ["object_id"],
            },
        },
        {
            "name": "get_relationships",
            "description": "Return CEPIO relationships and neighboring canonical objects for an object.",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string"},
                    "direction": {"type": "string", "enum": ["in", "out", "both"]},
                    "relationship_type": {"type": ["string", "null"]},
                },
                "required": ["object_id"],
            },
        },
        {
            "name": "get_events",
            "description": "Get operational CEPIO events recorded for a canonical object.",
            "parameters": {
                "type": "object",
                "properties": {"object_id": {"type": "string"}},
                "required": ["object_id"],
            },
        },
        {
            "name": "resolve_identity",
            "description": "Resolve a source-system alias or tag to a canonical CEPIO industrial object.",
            "parameters": {
                "type": "object",
                "properties": {"alias": {"type": "string"}},
                "required": ["alias"],
            },
        },
        {
            "name": "get_evidence",
            "description": "Retrieve CEPIO-bound source-native evidence references for a scenario, equipment object or modality.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_id": {"type": ["string", "null"]},
                    "equipment_id": {"type": ["string", "null"]},
                    "modality": {"type": ["string", "null"]},
                },
            },
        },
        {
            "name": "query_measurements",
            "description": "Retrieve CEPIO condition-signal summaries for equipment, optionally filtered by metric.",
            "parameters": {
                "type": "object",
                "properties": {
                    "equipment_id": {"type": "string"},
                    "metric": {"type": ["string", "null"]},
                },
                "required": ["equipment_id"],
            },
        },
        {
            "name": "get_provenance",
            "description": "Retrieve CEPIO provenance for an object or one of its semantic properties.",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string"},
                    "property_name": {"type": ["string", "null"]},
                },
                "required": ["object_id"],
            },
        },
    ]

    def __init__(self, runtime) -> None:
        self.runtime = runtime
        self.trace: list[dict[str, Any]] = []
        self.unknown_tool_attempts = 0
        self._call_counter = 0

    def reset_trace(self) -> None:
        self.trace = []
        self.unknown_tool_attempts = 0
        self._call_counter = 0

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        return self.TOOL_SCHEMAS

    def _record(self, name: str, arguments: dict[str, Any], result: Any, elapsed_ms: float, approved: bool) -> str:
        self._call_counter += 1
        call_id = f"tc-{self._call_counter:02d}"
        self.trace.append(
            {
                "id": call_id,
                "tool": name,
                "arguments": arguments,
                "approved": approved,
                "elapsed_ms": round(elapsed_ms, 3),
                "result": result,
            }
        )
        return call_id

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> tuple[str, Any]:
        arguments = arguments or {}
        started = time.perf_counter()
        if name not in APPROVED_TOOLS:
            self.unknown_tool_attempts += 1
            result = {"error": f"Tool is not exposed by CEPIO Agent Challenge: {name}"}
            elapsed_ms = (time.perf_counter() - started) * 1000
            call_id = self._record(name, arguments, result, elapsed_ms, approved=False)
            return call_id, result
        try:
            result = getattr(self, f"_tool_{name}")(**arguments)
        except Exception as exc:
            result = {"error": f"{type(exc).__name__}: {exc}"}
        elapsed_ms = (time.perf_counter() - started) * 1000
        call_id = self._record(name, arguments, result, elapsed_ms, approved=True)
        return call_id, result

    def _tool_search_objects(self, query: str, object_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        candidates = self.runtime.list_objects(object_type)
        query_tokens = {token for token in _norm(query).replace("-", " ").split() if token}
        scored: list[tuple[int, str, Any]] = []
        for obj in candidates:
            searchable_properties = {
                key: value
                for key, value in obj.properties.items()
                if key not in {"source_uri", "geospatial_source_uri"}
            }
            haystack = _norm(" ".join([obj.id, obj.type, obj.name, *_flatten(searchable_properties)]))
            score = sum(1 for token in query_tokens if token in haystack)
            if not query_tokens or score:
                scored.append((score, obj.id, obj))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [_object_view(obj) for _, _, obj in scored[: max(1, min(int(limit), 50))]]

    def _tool_get_object(self, object_id: str) -> dict[str, Any]:
        return _object_view(self.runtime.get_object(object_id))

    def _tool_get_relationships(
        self,
        object_id: str,
        direction: str = "both",
        relationship_type: str | None = None,
    ) -> list[dict[str, Any]]:
        self.runtime.get_object(object_id)
        directions = ["out", "in"] if direction == "both" else [direction]
        result: list[dict[str, Any]] = []
        for current_direction in directions:
            for rel in self.runtime.object_repository.get_relationships(object_id, direction=current_direction):
                if relationship_type and rel.type != relationship_type:
                    continue
                neighbor_id = rel.target.id if current_direction == "out" else rel.source.id
                result.append(
                    {
                        "relationship_type": rel.type,
                        "direction": current_direction,
                        "neighbor": _object_view(self.runtime.get_object(neighbor_id)),
                    }
                )
        return result

    def _tool_get_events(self, object_id: str) -> list[dict[str, Any]]:
        events = self.runtime.events_for(object_id)
        return [
            {
                "id": event.id,
                "type": event.type,
                "occurred_at": event.occurred_at.isoformat(),
                "severity": event.severity,
                "properties": event.properties,
            }
            for event in events
        ]

    def _tool_resolve_identity(self, alias: str) -> dict[str, Any] | None:
        target = _norm(alias)
        for obj in self.runtime.list_objects():
            candidates = [obj.id, obj.properties.get("canonical_iri", ""), obj.properties.get("source_tag", "")]
            aliases = obj.properties.get("aliases", {})
            if isinstance(aliases, dict):
                candidates.extend(aliases.values())
            if target in {_norm(value) for value in candidates if value}:
                return {
                    "canonical_object": _object_view(obj),
                    "canonical_iri": obj.properties.get("canonical_iri"),
                }
        return None

    def _tool_get_evidence(
        self,
        scenario_id: str | None = None,
        equipment_id: str | None = None,
        modality: str | None = None,
    ) -> list[dict[str, Any]]:
        result = []
        for obj in self.runtime.list_objects():
            current_modality = obj.properties.get("modality")
            if not current_modality:
                continue
            if scenario_id and obj.properties.get("scenario_id") != scenario_id:
                continue
            if equipment_id and obj.properties.get("equipment_id") != equipment_id:
                continue
            if modality and current_modality != modality:
                continue
            result.append(
                {
                    "artifact_id": obj.id,
                    "modality": current_modality,
                    "scenario_id": obj.properties.get("scenario_id"),
                    "equipment_id": obj.properties.get("equipment_id"),
                    "canonical_asset_iri": obj.properties.get("source_asset_iri"),
                    "event_time": obj.properties.get("event_time"),
                    "claims": obj.properties.get("ground_truth_claims", []),
                    "source_ref": obj.properties.get("source_uri"),
                    "provenance": obj.properties.get("provenance"),
                    "raw_payload_embedded": obj.properties.get("raw_payload_embedded"),
                }
            )
        return sorted(result, key=lambda item: item["artifact_id"])

    def _tool_query_measurements(self, equipment_id: str, metric: str | None = None) -> list[dict[str, Any]]:
        result = []
        for obj in self.runtime.reverse_neighbors(equipment_id, "observedOnEquipment"):
            if metric and obj.properties.get("metric") != metric:
                continue
            result.append(
                {
                    "signal_id": obj.id,
                    "metric": obj.properties.get("metric"),
                    "unit": obj.properties.get("unit"),
                    "sample_count": obj.properties.get("sample_count"),
                    "min": obj.properties.get("min"),
                    "max": obj.properties.get("max"),
                    "mean": obj.properties.get("mean"),
                    "pre_failure_mean": obj.properties.get("pre_failure_mean"),
                    "post_repair_mean": obj.properties.get("post_repair_mean"),
                    "repair_normalized": obj.properties.get("repair_normalized"),
                }
            )
        return sorted(result, key=lambda item: item["signal_id"])

    def _tool_get_provenance(self, object_id: str, property_name: str | None = None) -> dict[str, Any]:
        obj = self.runtime.get_object(object_id)
        source_ref = obj.properties.get("source_uri") or obj.properties.get("geospatial_source_uri")
        payload = {
            "object_id": obj.id,
            "source_ref": source_ref,
            "scenario_id": obj.properties.get("scenario_id"),
            "synthetic": True,
        }
        if property_name:
            payload["property_name"] = property_name
            payload["value"] = obj.properties.get(property_name)
        return payload


def _final(refs: list[Any], values: list[Any], calls: list[str], answer: str) -> dict[str, Any]:
    normalized_refs = list(dict.fromkeys(str(ref) for ref in refs if ref is not None))
    valid_calls = list(dict.fromkeys(calls))
    return {
        "answer": answer,
        "refs": normalized_refs,
        "values": values,
        "claims": [{"text": answer, "supported_by": valid_calls}],
        "confidence": 0.9,
    }


class ReferenceToolAgent:
    """Harness-validation agent. This is not an AI benchmark result."""

    def run(self, question: str, gateway: CEPIOToolGateway) -> dict[str, Any]:
        q = question.lower()
        calls: list[str] = []

        def call(name: str, **kwargs: Any) -> Any:
            call_id, result = gateway.call(name, kwargs)
            calls.append(call_id)
            return result

        if "most realized npt" in q and "rig-07" in q:
            downtime = call("search_objects", query="rig-07", object_type="DowntimeEvent", limit=20)
            event = max(downtime, key=lambda item: float(item["properties"].get("duration_hours", 0.0)))
            equipment_id = event["properties"]["equipment_id"]
            failures = call("search_objects", query=equipment_id, object_type="FailureEvent", limit=20)
            failure = failures[0]
            relationships = call("get_relationships", object_id=failure["id"], direction="out")
            work = next(item["neighbor"]["id"] for item in relationships if item["relationship_type"] == "repairedByWorkOrder")
            return _final(
                [equipment_id, failure["id"], event["id"], work],
                [event["properties"]["duration_hours"]],
                calls,
                f"{equipment_id} caused the largest Rig-07 NPT; {failure['id']} was repaired by {work}.",
            )

        if "active maintenance item" in q and "rig-12" in q:
            work = call("search_objects", query="open rig-12", object_type="WorkOrder", limit=20)
            item = work[0]
            equipment_id = item["properties"]["equipment_id"]
            call("get_object", object_id=equipment_id)
            return _final(
                [item["properties"]["scenario_id"], equipment_id, item["id"]],
                [],
                calls,
                f"{item['id']} is the open proactive item on {equipment_id}.",
            )

        if "independent evidence" in q and "valve sticking" in q:
            equipment = call("search_objects", query="rig-12 mud pump 2", object_type="DrillingEquipment", limit=10)[0]
            evidence = call("get_evidence", equipment_id=equipment["id"])
            modalities = sorted({item["modality"] for item in evidence if item["modality"] != "geospatial"})
            return _final(
                [equipment["id"], equipment["properties"]["scenario_id"], *modalities],
                [],
                calls,
                f"CEPIO binds {len(evidence)} evidence artifacts across {', '.join(modalities)}.",
            )

        if "improve after maintenance" in q and "rig-07" in q:
            equipment = call("search_objects", query="rig-07 mud pump 1", object_type="DrillingEquipment", limit=10)[0]
            signals = call("query_measurements", equipment_id=equipment["id"])
            work = call("search_objects", query=equipment["id"], object_type="WorkOrder", limit=20)
            relevant = [item for item in signals if item["metric"] in {"vibration_rms", "bearing_temperature"}]
            improved = bool(relevant) and all(item.get("repair_normalized") is True for item in relevant)
            return _final(
                [equipment["id"], *[item["metric"] for item in relevant], *[item["id"] for item in work]],
                [improved],
                calls,
                "The post-maintenance condition signals normalized." if improved else "The condition signals did not demonstrate normalization.",
            )

        if "bop failure" in q and "downtime" in q:
            equipment = call("search_objects", query="bop rig-21", object_type="DrillingEquipment", limit=10)[0]
            failures = call("search_objects", query=equipment["id"], object_type="FailureEvent", limit=10)
            failure = failures[0]
            relationships = call("get_relationships", object_id=failure["id"], direction="out")
            downtime = next(item["neighbor"] for item in relationships if item["relationship_type"] == "causesDowntime")
            work = next(item["neighbor"] for item in relationships if item["relationship_type"] == "repairedByWorkOrder")
            return _final(
                [equipment["id"], failure["id"], downtime["id"], work["id"]],
                [downtime["properties"]["duration_hours"]],
                calls,
                f"{failure['id']} on {equipment['id']} caused {downtime['properties']['duration_hours']} h of downtime and was addressed by {work['id']}.",
            )

        if "mp-001" in q and "resolve" in q:
            resolved = call("resolve_identity", alias="MP-001")
            return _final(
                [resolved["canonical_iri"]],
                [],
                calls,
                f"MP-001 resolves to {resolved['canonical_iri']}.",
            )

        if "well-02" in q and "well-05" in q and "well-08" in q:
            wells = []
            for well_id in ("well-02", "well-05", "well-08"):
                wells.append(call("get_object", object_id=well_id))
            rig_ids = {item["properties"]["rig_id"] for item in wells}
            rig_id = sorted(rig_ids)[0]
            call("get_object", object_id=rig_id)
            return _final(
                [rig_id, *[item["id"] for item in wells]],
                [],
                calls,
                f"{rig_id} is associated with all three wells.",
            )

        if "proactive-maintenance" in q or "proactive maintenance" in q:
            open_work = call("search_objects", query="open", object_type="WorkOrder", limit=20)
            item = open_work[0]
            equipment_id = item["properties"]["equipment_id"]
            failures = call("search_objects", query=equipment_id, object_type="FailureEvent", limit=20)
            downtime = call("search_objects", query=equipment_id, object_type="DowntimeEvent", limit=20)
            return _final(
                [item["properties"]["scenario_id"], equipment_id, item["id"]],
                [not failures and not downtime],
                calls,
                f"{item['properties']['scenario_id']} is proactive: {item['id']} is open before a failure or NPT event.",
            )

        if "scn-004" in q and "non-tabular" in q:
            evidence = call("get_evidence", scenario_id="SCN-004")
            modalities = sorted({item["modality"] for item in evidence if item["modality"] != "geospatial"})
            return _final(
                ["SCN-004", *modalities],
                [],
                calls,
                f"SCN-004 has CEPIO-bound evidence in {', '.join(modalities)}.",
            )

        if "maintenance superintendent" in q and "realized npt" in q:
            downtime = call("search_objects", query="", object_type="DowntimeEvent", limit=50)
            event = max(downtime, key=lambda item: float(item["properties"].get("duration_hours", 0.0)))
            return _final(
                [event["properties"]["scenario_id"], event["properties"]["equipment_id"], event["id"]],
                [event["properties"]["duration_hours"]],
                calls,
                f"Prioritize {event['properties']['scenario_id']} because {event['id']} has the largest realized NPT at {event['properties']['duration_hours']} h.",
            )

        return _final([], [], calls, "Unable to resolve the question using the bounded CEPIO tool surface.")


class ExternalProcessAgent:
    """JSONL adapter for a real model/agent process."""

    def __init__(self, command: str, timeout_seconds: float = 60.0) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _write(proc: subprocess.Popen[str], payload: dict[str, Any]) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        proc.stdin.flush()

    def _read(self, proc, messages, deadline: float) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Agent process exceeded challenge timeout")
        try:
            line = messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError("Agent process did not produce a response before timeout") from exc
        if line is None:
            raise RuntimeError("Agent process exited before final answer")
        return json.loads(line)

    def run(self, question: str, gateway: CEPIOToolGateway) -> dict[str, Any]:
        proc = subprocess.Popen(
            shlex.split(self.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        messages: queue.Queue[str | None] = queue.Queue()
        stderr_tail: deque[str] = deque(maxlen=80)

        def read_stdout() -> None:
            try:
                for line in proc.stdout:
                    messages.put(line)
            finally:
                messages.put(None)

        def read_stderr() -> None:
            if proc.stderr is not None:
                for line in proc.stderr:
                    stderr_tail.append(line[-8000:])

        readers = [threading.Thread(target=read_stdout, daemon=True),
                   threading.Thread(target=read_stderr, daemon=True)]
        for reader in readers:
            reader.start()
        deadline = time.monotonic() + self.timeout_seconds
        try:
            self._write(
                proc,
                {
                    "type": "challenge",
                    "question": question,
                    "tools": gateway.tool_schemas,
                    "final_schema": {
                        "answer": "string",
                        "refs": ["string"],
                        "values": ["number|string|boolean"],
                        "claims": [{"text": "string", "supported_by": ["tool_call_id"]}],
                        "confidence": "0..1",
                    },
                },
            )
            while True:
                message = self._read(proc, messages, deadline)
                if message.get("type") == "tool_call":
                    requested_id = str(message.get("id", "agent-call"))
                    call_id, result = gateway.call(str(message.get("name")), message.get("arguments") or {})
                    self._write(
                        proc,
                        {
                            "type": "tool_result",
                            "request_id": requested_id,
                            "tool_call_id": call_id,
                            "result": result,
                        },
                    )
                    continue
                if message.get("type") == "final":
                    answer = message.get("answer")
                    if not isinstance(answer, dict):
                        raise ValueError("Final agent message must contain an answer object")
                    return answer
                raise ValueError(f"Unknown agent protocol message: {message}")
        except (TimeoutError, RuntimeError) as exc:
            raise type(exc)(f"{exc} Child stderr tail:\n{''.join(stderr_tail.copy())[-8000:]}") from exc
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
            for reader in readers:
                reader.join(timeout=2)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()


def _value_matches(expected: Any, observed: Any) -> bool:
    if isinstance(expected, bool):
        return isinstance(observed, bool) and expected is observed
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return math.isclose(float(expected), float(observed), rel_tol=1e-6, abs_tol=1e-6)
        except (TypeError, ValueError):
            return False
    return _norm(expected) == _norm(observed)


def _score_answer(expected: dict[str, Any], answer: dict[str, Any], trace: list[dict[str, Any]]) -> dict[str, Any]:
    answer_refs = {_norm(item) for item in answer.get("refs", [])}
    missing_refs = [item for item in expected.get("expected_refs", []) if _norm(item) not in answer_refs]
    answer_values = answer.get("values", [])
    missing_values = [
        item
        for item in expected.get("expected_values", [])
        if not any(_value_matches(item, observed) for observed in answer_values)
    ]
    valid_call_ids = {item["id"] for item in trace if item.get("approved")}
    unsupported_claims = []
    claims = answer.get("claims", [])
    for claim in claims:
        supported_by = claim.get("supported_by", []) if isinstance(claim, dict) else []
        if not supported_by or any(call_id not in valid_call_ids for call_id in supported_by):
            unsupported_claims.append(claim)
    evidence_ok = bool(claims) and not unsupported_claims and bool(valid_call_ids)
    return {
        "passed": not missing_refs and not missing_values,
        "missing_refs": missing_refs,
        "missing_values": missing_values,
        "evidence_ok": evidence_ok,
        "unsupported_claims": len(unsupported_claims),
    }


def build_challenge_runtime(output: Path, telemetry_points: int, waveform_samples: int, seed: int = 1701):
    acceptance = _load_acceptance_module()
    generator = acceptance._load_v02_generator()
    generator.generate_multimodal_dataset(
        output,
        telemetry_points=telemetry_points,
        waveform_samples=waveform_samples,
        seed=seed,
    )
    runtime = acceptance.build_acceptance_runtime(output)
    return runtime


def run_challenge(
    *,
    agent_kind: str = "reference",
    agent_command: str | None = None,
    telemetry_points: int = 600,
    waveform_samples: int = 512,
    seed: int = 1701,
    output: Path | None = None,
) -> dict[str, Any]:
    questions_doc = _read_json(BENCHMARK / "questions.json")
    hidden_doc = _read_json(BENCHMARK / "hidden-evaluator.json")
    expected_by_id = {item["id"]: item for item in hidden_doc["answers"]}

    managed_tmp = tempfile.TemporaryDirectory(prefix="cepio-agent-challenge-") if output is None else None
    dataset_dir = Path(managed_tmp.name) if managed_tmp is not None else output
    assert dataset_dir is not None
    runtime = build_challenge_runtime(dataset_dir, telemetry_points, waveform_samples, seed)
    gateway = CEPIOToolGateway(runtime)

    if agent_kind == "reference":
        agent = ReferenceToolAgent()
    elif agent_kind == "external":
        if not agent_command:
            raise ValueError("--agent-command is required for --agent external")
        agent = ExternalProcessAgent(agent_command)
    else:
        raise ValueError(f"Unsupported agent kind: {agent_kind}")

    details = []
    latencies = []
    call_counts = []
    unsupported_total = 0
    evidence_passed = 0
    passed = 0
    identity_passed = 0
    identity_total = 0
    leakage_attempts = 0

    try:
        for item in questions_doc["questions"]:
            question_text = str(item["question"])
            gateway.reset_trace()
            started = time.perf_counter()
            answer = agent.run(question_text, gateway)
            elapsed_ms = (time.perf_counter() - started) * 1000
            score = _score_answer(expected_by_id[item["id"]], answer, gateway.trace)

            passed += int(score["passed"])
            evidence_passed += int(score["evidence_ok"])
            unsupported_total += int(score["unsupported_claims"])
            leakage_attempts += gateway.unknown_tool_attempts
            latencies.append(elapsed_ms)
            call_counts.append(len(gateway.trace))
            if expected_by_id[item["id"]].get("identity_question"):
                identity_total += 1
                identity_passed += int(score["passed"])

            details.append(
                {
                    "id": item["id"],
                    "level": item["level"],
                    "question": question_text,
                    "passed": score["passed"],
                    "evidence_ok": score["evidence_ok"],
                    "unsupported_claims": score["unsupported_claims"],
                    "missing_refs": score["missing_refs"],
                    "missing_values": score["missing_values"],
                    "tool_calls": len(gateway.trace),
                    "latency_ms": round(elapsed_ms, 3),
                    "answer": answer,
                    "trace": gateway.trace,
                }
            )
    finally:
        if managed_tmp is not None:
            managed_tmp.cleanup()

    total = len(details)
    accuracy = passed / total if total else 0.0
    evidence_coverage = evidence_passed / total if total else 0.0
    identity_accuracy = identity_passed / identity_total if identity_total else None
    median_calls = statistics.median(call_counts) if call_counts else 0.0
    median_latency = statistics.median(latencies) if latencies else 0.0
    thresholds = {
        "accuracy": 0.80 if agent_kind == "external" else 1.0,
        "evidence_coverage": 1.0,
        "unsupported_claims": 0,
        "identity_accuracy": 0.95,
        "median_tool_calls": 8.0,
        "semantic_abstraction_leakage": 0,
    }
    gate_passed = (
        accuracy >= thresholds["accuracy"]
        and evidence_coverage >= thresholds["evidence_coverage"]
        and unsupported_total == 0
        and (identity_accuracy is None or identity_accuracy >= thresholds["identity_accuracy"])
        and median_calls <= thresholds["median_tool_calls"]
        and leakage_attempts == 0
    )
    return {
        "benchmark": questions_doc["benchmark"],
        "dataset_version": questions_doc["dataset_version"],
        "agent_kind": agent_kind,
        "agent_input": "question_text_plus_cepio_tool_schemas_only",
        "direct_source_access": False,
        "expected_answers_visible_during_answering": False,
        "passed": passed,
        "total": total,
        "accuracy": accuracy,
        "evidence_passed": evidence_passed,
        "evidence_coverage": evidence_coverage,
        "unsupported_claims": unsupported_total,
        "identity_accuracy": identity_accuracy,
        "median_tool_calls": median_calls,
        "median_latency_ms": round(median_latency, 3),
        "semantic_abstraction_leakage": leakage_attempts,
        "thresholds": thresholds,
        "gate_passed": gate_passed,
        "details": details,
    }


def _summary(report: dict[str, Any]) -> str:
    failed = [item["id"] for item in report["details"] if not item["passed"]]
    return (
        "CEPIO_AGENT_CHALLENGE "
        f"agent={report['agent_kind']} "
        f"passed={report['passed']}/{report['total']} "
        f"accuracy={report['accuracy']:.3f} "
        f"evidence={report['evidence_coverage']:.3f} "
        f"unsupported={report['unsupported_claims']} "
        f"median_calls={report['median_tool_calls']:.1f} "
        f"median_latency_ms={report['median_latency_ms']:.1f} "
        f"leakage={report['semantic_abstraction_leakage']} "
        f"failed={','.join(failed) if failed else 'none'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated CEPIO Agent Challenge v0.1.")
    parser.add_argument("--agent", choices=["reference", "external"], default="reference")
    parser.add_argument("--agent-command")
    parser.add_argument("--telemetry-points", type=int, default=600)
    parser.add_argument("--waveform-samples", type=int, default=512)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = run_challenge(
        agent_kind=args.agent,
        agent_command=args.agent_command,
        telemetry_points=args.telemetry_points,
        waveform_samples=args.waveform_samples,
        seed=args.seed,
        output=args.output,
    )
    print(_summary(report))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
