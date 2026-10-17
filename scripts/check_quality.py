"""Static debt is explicit; new lint/type findings and unformatted edits fail."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "quality/static-baseline.json"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stdout + result.stderr)
    return result


def key(tool: str, path: str, line: int, message: str) -> str:
    relative = Path(path).resolve().relative_to(ROOT).as_posix()
    source = (ROOT / relative).read_text(encoding="utf-8").splitlines()[line - 1].strip()
    return json.dumps([tool, relative, message, source])


def findings() -> Counter[str]:
    result: Counter[str] = Counter()
    lint = run(
        sys.executable, "-m", "ruff", "check", "src", "tests", "scripts", "--output-format=json"
    )
    for item in json.loads(lint.stdout):
        result[
            key(
                "ruff",
                item["filename"],
                item["location"]["row"],
                item["code"] + ": " + item["message"],
            )
        ] += 1
    types = run(sys.executable, "-m", "mypy", "src/cepio", "--no-pretty", "--no-error-summary")
    for line in types.stdout.splitlines():
        match = re.match(r"(.+?):(\d+): error: (.*)", line)
        if match:
            result[key("mypy", match[1], int(match[2]), match[3])] += 1
        elif line and ": note:" not in line:
            raise RuntimeError("Unrecognized mypy diagnostic: " + line)
    if types.returncode and not any('"mypy"' in item for item in result):
        raise RuntimeError(types.stdout + types.stderr)
    return result


def changed_python(base: str) -> list[str]:
    diff = run("git", "diff", "--name-only", "--diff-filter=ACMR", base, "--", "*.py")
    if diff.returncode:
        raise RuntimeError(diff.stderr)
    untracked = run("git", "ls-files", "--others", "--exclude-standard", "--", "*.py")
    return sorted(set(diff.stdout.splitlines() + untracked.stdout.splitlines()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--record-baseline", action="store_true")
    args = parser.parse_args()
    current = findings()
    if args.record_baseline:
        BASELINE.parent.mkdir(exist_ok=True)
        BASELINE.write_text(
            json.dumps(dict(sorted(current.items())), indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"Recorded {sum(current.values())} existing findings; review baseline changes explicitly."
        )
        return 0
    accepted = Counter(json.loads(BASELINE.read_text(encoding="utf-8")))
    new = current - accepted
    for finding, count in new.items():
        print(f"NEW ({count}): {finding}")
    paths = changed_python(args.base)
    formatted = run(sys.executable, "-m", "ruff", "format", "--check", *paths) if paths else None
    if formatted:
        print(formatted.stdout + formatted.stderr)
    print(f"Existing static debt: {sum(current.values())}; new findings: {sum(new.values())}")
    return int(bool(new) or bool(formatted and formatted.returncode))


if __name__ == "__main__":
    raise SystemExit(main())
