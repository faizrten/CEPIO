"""Compare actual base and head coverage under the same CI environment."""

import json
from pathlib import Path
import sys


def percentage(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["totals"]["percent_covered"]


if __name__ == "__main__":
    before, after = map(percentage, sys.argv[1:])
    print(f"Coverage base={before:.6f}% head={after:.6f}%")
    raise SystemExit(int(after + 0.000001 < before))
