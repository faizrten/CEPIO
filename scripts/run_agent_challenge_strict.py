from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts/run_agent_challenge.py"

spec = importlib.util.spec_from_file_location("cepio_agent_challenge_base", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


def _tokens(value: Any) -> set[str]:
    result: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", str(value).lower()):
        if token.isdigit():
            result.add(str(int(token)))
        else:
            result.add(token)
    return result


def _strict_search_objects(self, query: str, object_type: str | None = None, limit: int = 20):
    candidates = self.runtime.list_objects(object_type)
    query_tokens = _tokens(query)
    scored = []
    complete = []
    for obj in candidates:
        searchable_properties = {
            key: value
            for key, value in obj.properties.items()
            if key not in {"source_uri", "geospatial_source_uri"}
        }
        identity_tokens = _tokens(f"{obj.id} {obj.name}")
        haystack_tokens = _tokens(" ".join([obj.id, obj.type, obj.name, *base._flatten(searchable_properties)]))
        overlap = query_tokens.intersection(haystack_tokens)
        identity_overlap = query_tokens.intersection(identity_tokens)
        score = len(overlap) + (2 * len(identity_overlap))
        entry = (score, len(identity_overlap), obj.id, obj)
        if query_tokens and query_tokens.issubset(haystack_tokens):
            complete.append(entry)
        elif not query_tokens or score:
            scored.append(entry)
    selected = complete if complete else scored
    selected.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [base._object_view(obj) for _, _, _, obj in selected[: max(1, min(int(limit), 50))]]


base.CEPIOToolGateway._tool_search_objects = _strict_search_objects


class StrictReferenceToolAgent(base.ReferenceToolAgent):
    """Reference harness with question-faithful semantic search; not an AI result."""

    def run(self, question: str, gateway):
        q = question.lower()
        if "independent evidence" in q and "valve sticking" in q:
            calls: list[str] = []

            def call(name: str, **kwargs: Any):
                call_id, result = gateway.call(name, kwargs)
                calls.append(call_id)
                return result

            equipment = call("search_objects", query=question, object_type="DrillingEquipment", limit=10)[0]
            evidence = call("get_evidence", equipment_id=equipment["id"])
            modalities = sorted({item["modality"] for item in evidence if item["modality"] != "geospatial"})
            return base._final(
                [equipment["id"], equipment["properties"]["scenario_id"], *modalities],
                [],
                calls,
                f"CEPIO binds {len(evidence)} evidence artifacts across {', '.join(modalities)}.",
            )
        return super().run(question, gateway)


class StrictExternalProcessAgent(base.ExternalProcessAgent):
    """External agent adapter with model-friendly timeout and diagnostic stderr capture."""

    def __init__(self, command: str, timeout_seconds: float = 120.0) -> None:
        super().__init__(command, timeout_seconds=timeout_seconds)


base.ReferenceToolAgent = StrictReferenceToolAgent
base.ExternalProcessAgent = StrictExternalProcessAgent

APPROVED_TOOLS = base.APPROVED_TOOLS
BENCHMARK = base.BENCHMARK
CEPIOToolGateway = base.CEPIOToolGateway
_read_json = base._read_json
_score_answer = base._score_answer
run_challenge = base.run_challenge


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
