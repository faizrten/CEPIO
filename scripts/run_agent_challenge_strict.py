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
    for obj in candidates:
        searchable_properties = {
            key: value
            for key, value in obj.properties.items()
            if key not in {"source_uri", "geospatial_source_uri"}
        }
        haystack_tokens = _tokens(" ".join([obj.id, obj.type, obj.name, *base._flatten(searchable_properties)]))
        score = len(query_tokens.intersection(haystack_tokens))
        if not query_tokens or score:
            scored.append((score, obj.id, obj))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [base._object_view(obj) for _, _, obj in scored[: max(1, min(int(limit), 50))]]


base.CEPIOToolGateway._tool_search_objects = _strict_search_objects

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
