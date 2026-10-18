from __future__ import annotations

import importlib.util
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
