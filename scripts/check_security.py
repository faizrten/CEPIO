"""Accept only reviewed Bandit source findings, never an entire file/rule pair."""

from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys


def fingerprint(issue):
    code = re.sub(r"(?m)^\d+\s+", "", issue["code"]).strip()
    filename = issue["filename"].replace("\\", "/").removeprefix("./")
    return (
        filename,
        issue["test_id"],
        issue["issue_text"],
        issue["issue_severity"],
        issue["issue_confidence"],
        code,
    )


def unexpected(current, accepted):
    return Counter(map(fingerprint, current)) - Counter(map(fingerprint, accepted))


def main():
    output = Path("evidence/bandit.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", "src", "-ll", "-f", "json", "-o", str(output)],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stdout + result.stderr)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("errors"):
        raise RuntimeError(report["errors"])
    baseline = json.loads(Path("quality/bandit-baseline.json").read_text(encoding="utf-8"))
    new = unexpected(report["results"], baseline["results"])
    for finding, count in new.items():
        print(f"NEW SECURITY FINDING ({count}): {finding}")
    print(
        f"Reviewed security exceptions: {len(baseline['results'])}; new findings: {sum(new.values())}"
    )
    return int(bool(new))


if __name__ == "__main__":
    raise SystemExit(main())
